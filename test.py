import re
import numpy as np
from manim import (
    Scene, VGroup, Mobject, AnimationGroup,
    FadeOut, FadeIn, Transform, FadeTransformPieces,
    Code, config, Create, Write
)
from manim.mobject.geometry.arc import Dot
from manim.mobject.svg.svg_mobject import SVGMobject
from manim.mobject.text.text_mobject import Text
from manim.utils.color import ManimColor


################################################################################
# 1) LineVGroup: 라인 하나를 담는 VGroup. .text 속성 보관
################################################################################
class LineVGroup(VGroup):
    def __init__(self, *submobjects, text=""):
        super().__init__(*submobjects)
        self.text = text  # "한 줄"에 해당하는 최종 문자열을 보관


################################################################################
# 2) Paragraph: 라인 단위로 .text를 가지는 객체
################################################################################
class Paragraph(VGroup):
    """
    - 각 줄을 LineVGroup으로 만들어 .text를 저장
    - self.chars = VGroup([...]) 형태로 라인별 submobject
    """

    def __init__(
        self,
        *text: str,
        line_spacing: float = -1,
        alignment: str | None = None,
        **kwargs,
    ):
        self.line_spacing = line_spacing
        self.alignment = alignment
        # Manim에서 disable_ligatures가 "공백 무시"와는 무관하지만, 예시로 사용
        self.consider_spaces_as_chars = kwargs.get("disable_ligatures", False)

        super().__init__()

        # (A) 합쳐서 하나의 Text(...) 생성
        lines_str = "\n".join(list(text))
        self.lines_text = Text(lines_str, line_spacing=line_spacing, **kwargs)
        lines_str_list = lines_str.split("\n")

        # (B) 라인별 VGroup 생성
        self.chars = self._gen_chars(lines_str_list)

        # (C) self.lines 구조
        self.lines = [list(self.chars), [self.alignment] * len(self.chars)]
        self.lines_initial_positions = [line.get_center() for line in self.lines[0]]

        # (D) 최종 VGroup에 추가
        self.add(*self.lines[0])
        self.move_to(np.array([0, 0, 0]))

        if self.alignment:
            self._set_all_lines_alignments(self.alignment)

    def _gen_chars(self, lines_str_list: list[str]) -> VGroup:
        """각 줄 => LineVGroup(..., text=...)"""
        total_lines_group = VGroup()
        char_index_counter = 0

        for line_no, line_str in enumerate(lines_str_list):
            # 1) 표시할 문자 개수 (공백 제외 vs 포함)
            if self.consider_spaces_as_chars:
                char_count = len(line_str)
            else:
                # 공백은 무시
                char_count = sum(1 for c in line_str if not c.isspace())

            # 2) self.lines_text.chars[...] 슬라이싱
            line_chars = self.lines_text.chars[
                char_index_counter : char_index_counter + char_count
            ]

            # 3) 실제 라인 문자열 (공백 제거할지 여부 선택)
            if self.consider_spaces_as_chars:
                line_text = line_str
            else:
                line_text = re.sub(r"\s+", "", line_str)  # 모든 공백 제거

            # 4) 한 줄용 VGroup(LineVGroup) 생성 -> text 속성 저장
            line_vgroup = LineVGroup(*line_chars, text=line_text)

            # 5) 인덱스 갱신
            char_index_counter += char_count
            if self.consider_spaces_as_chars:
                # 개행(\n)도 한 글자로 센다
                char_index_counter += 1

            total_lines_group.add(line_vgroup)

        return total_lines_group

    # 정렬 관련 메서드 (원본 그대로)
    def _set_all_lines_alignments(self, alignment: str):
        for line_no in range(len(self.lines[0])):
            self._change_alignment_for_a_line(alignment, line_no)
        return self

    def _set_line_alignment(self, alignment: str, line_no: int):
        self._change_alignment_for_a_line(alignment, line_no)
        return self

    def _set_all_lines_to_initial_positions(self):
        self.lines[1] = [None] * len(self.lines[0])
        for line_no in range(len(self.lines[0])):
            self[line_no].move_to(
                self.get_center() + self.lines_initial_positions[line_no]
            )
        return self

    def _set_line_to_initial_position(self, line_no: int):
        self.lines[1][line_no] = None
        self[line_no].move_to(
            self.get_center() + self.lines_initial_positions[line_no]
        )
        return self

    def _change_alignment_for_a_line(self, alignment: str, line_no: int):
        self.lines[1][line_no] = alignment
        line_obj = self[line_no]

        if alignment == "center":
            line_obj.move_to(
                np.array([self.get_center()[0], line_obj.get_center()[1], 0]),
            )
        elif alignment == "right":
            line_obj.move_to(
                np.array(
                    [
                        self.get_right()[0] - line_obj.width / 2,
                        line_obj.get_center()[1],
                        0,
                    ]
                ),
            )
        elif alignment == "left":
            line_obj.move_to(
                np.array(
                    [
                        self.get_left()[0] + line_obj.width / 2,
                        line_obj.get_center()[1],
                        0,
                    ]
                ),
            )


################################################################################
# 3) gather_text_no_whitespace: mobject 내부 .text를 찾아 모으고 공백 제거
################################################################################
def gather_text_no_whitespace(mobj: Mobject) -> str:
    result_texts = []

    def recurse(current: Mobject):
        for sm in current.submobjects:
            if hasattr(sm, "text") and isinstance(sm.text, str):
                result_texts.append(sm.text)
            if len(sm.submobjects) > 0:
                recurse(sm)

    recurse(mobj)
    joined = "".join(result_texts)
    # 모든 공백(\s) 제거
    no_space = re.sub(r"\s+", "", joined)
    return no_space


################################################################################
# 4) TransformMatchingPartsBase / TransformCode
#    - 라인 단위 매칭, get_mobject_parts, get_mobject_key
################################################################################
class TransformMatchingPartsBase(AnimationGroup):
    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        transform_mismatches: bool = False,
        fade_transform_mismatches: bool = False,
        key_map: dict | None = None,
        **kwargs,
    ):
        print("=============[ TransformMatchingPartsBase DEBUG ]================")
        print(f"[DEBUG] 초기 mobject: {mobject}")
        print(f"[DEBUG] 목표 target_mobject: {target_mobject}")

        anims = []

        source_map = self.get_shape_map(mobject, label="SOURCE")
        target_map = self.get_shape_map(target_mobject, label="TARGET")

        if key_map is None:
            key_map = {}

        # 공통 키
        common_keys = set(source_map).intersection(target_map)
        print(f"[DEBUG] 공통 KEY들 = {common_keys}")
        transform_source = VGroup()
        transform_target = VGroup()
        for k in common_keys:
            print(f"[DEBUG]   -> 공통 KEY '{k}' 매칭 (Transform)")
            transform_source.add(source_map[k])
            transform_target.add(target_map[k])

        if len(transform_source) > 0:
            anims.append(Transform(transform_source, transform_target, **kwargs))
        else:
            print("[DEBUG] => 공통 key가 없어서 Transform 애니메이션은 생성되지 않음")

        # key_map 처리
        key_mapped_source = VGroup()
        key_mapped_target = VGroup()
        for k1, k2 in key_map.items():
            if k1 in source_map and k2 in target_map:
                print(f"[DEBUG]   -> key_map '{k1}' -> '{k2}' (FadeTransformPieces)")
                key_mapped_source.add(source_map[k1])
                key_mapped_target.add(target_map[k2])
                source_map.pop(k1, None)
                target_map.pop(k2, None)

        if len(key_mapped_source) > 0:
            anims.append(FadeTransformPieces(key_mapped_source, key_mapped_target, **kwargs))

        unmatched_source_keys = set(source_map).difference(target_map)
        unmatched_target_keys = set(target_map).difference(source_map)
        print(f"[DEBUG] unmatched source keys = {unmatched_source_keys}")
        print(f"[DEBUG] unmatched target keys = {unmatched_target_keys}")

        fade_source = VGroup()
        fade_target = VGroup()

        for k in unmatched_source_keys:
            print(f"[DEBUG]   -> SOURCE '{k}' => FadeOut 대상")
            fade_source.add(source_map[k])
        for k in unmatched_target_keys:
            print(f"[DEBUG]   -> TARGET '{k}' => FadeIn 대상")
            fade_target.add(target_map[k])

        fade_target_copy = fade_target.copy()

        if transform_mismatches:
            anims.append(Transform(fade_source, fade_target, **kwargs))
        elif fade_transform_mismatches:
            anims.append(FadeTransformPieces(fade_source, fade_target, **kwargs))
        else:
            anims.append(FadeOut(fade_source, target_position=fade_target, **kwargs))
            anims.append(FadeIn(fade_target_copy, target_position=fade_target, **kwargs))

        super().__init__(*anims)
        self.to_remove = [mobject, fade_target_copy]
        self.to_add = target_mobject
        print("[DEBUG] => TransformMatchingPartsBase __init__ 완료\n")

    def get_shape_map(self, mobject: Mobject, label=""):
        shape_map = {}
        print(f"[DEBUG] get_shape_map START ({label}) => {mobject}")

        parts = self.get_mobject_parts(mobject)
        print(f"[DEBUG]   => get_mobject_parts() 결과 {len(parts)}개:")
        for i, p in enumerate(parts):
            print(f"            [{i}] {p}")

        for p in parts:
            key = self.get_mobject_key(p)
            print(f"[DEBUG]   -> PART: {p}, KEY='{key}'")
            if key not in shape_map:
                shape_map[key] = VGroup()
            shape_map[key].add(p)

        print(f"[DEBUG] get_shape_map ({label}) => shape_map 결과 key 목록: {list(shape_map.keys())}")
        return shape_map

    def clean_up_from_scene(self, scene: Scene):
        for anim in self.animations:
            anim.interpolate(0)
        scene.remove(self.mobject)
        scene.remove(*self.to_remove)
        scene.add(self.to_add)
        print("[DEBUG] clean_up_from_scene 완료.\n")

    @staticmethod
    def get_mobject_parts(mobject: Mobject):
        raise NotImplementedError()

    @staticmethod
    def get_mobject_key(mobject: Mobject):
        raise NotImplementedError()


class TransformCode(TransformMatchingPartsBase):
    """
    - Code 객체 -> submobjects[2] (코드 Paragraph).lines[0]
    - Paragraph -> paragraph.lines[0]
    - 그 외 fallback => submobjects
    - key: gather_text_no_whitespace => 모든 .text 모으고 공백 제거
    """

    @staticmethod
    def get_mobject_parts(mobject: Mobject):
        from manim.mobject.types.vectorized_mobject import VGroup

        if isinstance(mobject, Code):
            print("[DEBUG get_mobject_parts] Code 객체 감지!")
            # Code 객체: [0]=배경, [1]=줄번호 Paragraph, [2]=코드 내용 Paragraph
            if len(mobject.submobjects) >= 3:
                code_paragraph = mobject.submobjects[2]
                if hasattr(code_paragraph, "lines"):
                    print(
                        f"[DEBUG get_mobject_parts] -> code_paragraph.lines[0] (라인 수={len(code_paragraph.lines[0])})"
                    )
                    return code_paragraph.lines[0]
                else:
                    print("[DEBUG get_mobject_parts] -> code_paragraph.lines 없음 => fallback submobjects")
                    return code_paragraph.submobjects
            else:
                print("[DEBUG get_mobject_parts] -> Code submobjects < 3 => fallback")
                return mobject.submobjects

        # Paragraph
        if hasattr(mobject, "lines") and isinstance(mobject.lines, list):
            print(f"[DEBUG get_mobject_parts] Paragraph. lines[0] len={len(mobject.lines[0])}")
            return mobject.lines[0]

        # fallback
        print("[DEBUG get_mobject_parts] fallback => mobject.submobjects")
        return mobject.submobjects

    @staticmethod
    def get_mobject_key(mobject: Mobject):
        # 라인 mobject의 .text, 혹은 전체 submobject들 .text를 모으고 공백 제거
        line_str = gather_text_no_whitespace(mobject)
        print(f"[DEBUG get_mobject_key] => '{line_str}' (공백제거)")
        return line_str


################################################################################
# 5) Test Scenes
################################################################################

class ParagraphTest(Scene):
    def construct(self):
        p = Paragraph(
            "from manim import *",
            "class Animation(Scene):",
            "    def construct(self):",
            line_spacing=0.4
        )
        self.add(p)
        self.wait()

        # 각 라인(VGroup)에 text 속성이 제대로 들어있는지 체크
        for i, line_vgroup in enumerate(p.chars):
            print(f"[Line {i}] => '{line_vgroup.text}'")

class CodeAnimation(Scene):
    def construct(self):
        code1 = '''from manim import *

class Animation(Scene):
    def construct(self):
    
        square = Square(side_length=2.0, color=RED)
        
        self.play(Create(square))
        self.wait()
'''

        code2 = '''from manim import *

class Animation(Scene):
    def construct(self):
    
        square = Square(side_length=2.0, color=RED)
        
        square.shift(  LEFT   * 2 )
        
        self.play(Create(square))
        self.wait()
'''

        print("[Scene] CodeAnimation.construct() 시작")

        rendered_code1 = Code(
            code=code1,
            tab_width=4,
            background="window",
            language="Python",
            font="Monospace",
            style="one-dark",
            line_spacing=1
        )
        
        rendered_code2 = Code(
            code=code2,
            tab_width=4,
            background="window",
            language="Python",
            font="Monospace",
            style="one-dark",
            line_spacing=1
        )

        print("[Scene] => Write(rendered_code1)")
        self.play(Create(rendered_code1))
        self.wait()

        print("[Scene] => TransformCode(rendered_code1, rendered_code2)")
        self.play(TransformCode(rendered_code1, rendered_code2))
        self.wait()

        print("[Scene] CodeAnimation 끝\n")
        
        
class CodeScene(Scene):
    def construct(self):
        code1 = '''from manim import *

class Animation(Scene):
    def construct(self):

        square = Square(side_length=2.0, color=RED)

        self.play(Create(square))
        self.wait()
'''

        print("[Scene] CodeAnimation.construct() 시작")

        rendered_code1 = Code(
            code=code1,
            tab_width=4,
            background="window",
            language="Python",
            font="Monospace",
            style="one-dark",
            line_spacing=1
        )

        self.play(Create(rendered_code1))
        self.wait()

        # ------------------------------------------------------
        # 여기서: rendered_code1.submobjects[2] => "코드 내용 Paragraph"
        # 만약 insert_line_no=True 상태면:
        #   [0] = 배경, [1] = 줄번호 Paragraph, [2] = "코드 내용" Paragraph
        # ------------------------------------------------------
        code_paragraph = rendered_code1.submobjects[2]

        # code_paragraph.lines[0] => "라인들의 리스트"
        lines = code_paragraph.lines[0]

        print("[Debug] 코드 내용 Paragraph의 라인 수 =", len(lines))

        for i, line_vgroup in enumerate(lines):
            # line_vgroup: 한 줄(VGroup)
            # 일반 Paragraph면 line_vgroup 내의 text 속성은 없을 수도 있음
            # 하지만, 커스텀 Paragraph면 line_vgroup.text에 들어있을 수 있음
            print(f"[Line {i}] 객체: ", line_vgroup)
            # 만약 line_vgroup.text를 지원한다면:
            if hasattr(line_vgroup, "text"):
                print(f"       => line_vgroup.text = '{line_vgroup.text}'")

        # ------------------------------------------------------
        # 다른 동작 예시 (optional)
        # 예: 첫 번째 줄에 빨간 색칠
        # ------------------------------------------------------

        self.wait()
        print("[Scene] 끝")

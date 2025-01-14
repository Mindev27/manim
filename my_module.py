import re
from manim.mobject.text.text_mobject import Paragraph, Text
from manim.mobject.types.vectorized_mobject import VGroup

class LineVGroup(VGroup):
    """한 줄을 나타내는 VGroup. .text 속성에 실제 문자열을 기록."""
    def __init__(self, *submobjects, text=""):
        super().__init__(*submobjects)
        self.text = text


class CodeParagraph(Paragraph):
    def __init__(
        self,
        *text_lines,
        line_spacing=0.3,
        font_size=24,
        font="Monospace",
        consider_spaces_as_chars=False,
        **kwargs
    ):
        self.consider_spaces_as_chars = consider_spaces_as_chars
        super().__init__(
            *text_lines,
            line_spacing=line_spacing,
            font_size=font_size,
            font=font,
            disable_ligatures=True,
            **kwargs
        )

    def _gen_chars(self, lines_str_list: list) -> VGroup:
        import re
        from manim.mobject.types.vectorized_mobject import VGroup

        chars = VGroup()
        char_index_counter = 0
        for line_no, line_str in enumerate(lines_str_list):
            if self.consider_spaces_as_chars:
                char_count = len(line_str)
            else:
                char_count = sum(1 for c in line_str if not c.isspace())
            line_vgroup = VGroup()
            line_subm = self.lines_text.chars[
                char_index_counter : char_index_counter + char_count
            ]
            line_vgroup.add(*line_subm)

            # line_vgroup 에 .text 저장 (동적 attribute)
            if self.consider_spaces_as_chars:
                line_text = line_str
            else:
                line_text = re.sub(r"\s+", "", line_str)
            setattr(line_vgroup, "text", line_text)  # or use a small 'LineVGroup'

            char_index_counter += char_count
            if self.consider_spaces_as_chars:
                char_index_counter += 1
            chars.add(line_vgroup)
        return chars
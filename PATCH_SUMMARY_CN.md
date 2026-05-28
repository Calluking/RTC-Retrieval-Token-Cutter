# Django Media 排序修复

## 问题

合并 3 个或更多 media 对象时，即使不存在真实冲突，也可能抛出不必要的 `MediaOrderConflictWarning`。

## 根因

原始 `Media.merge()` 算法只要发现 `index > last_insert_index` 就会警告排序冲突，却没有判断这个冲突是否真的需要提示。因此在以下场景会产生误报：

1. 多个 media 对象按顺序合并。
2. 算法从中间合并结果中建立隐式顺序约束。
3. 后续合并提供了更完整的排序信息，而算法其实可以处理。

## 问题示例

```python
class ColorPicker(Widget):
    class Media:
        js = ['color-picker.js']

class SimpleTextWidget(Widget):
    class Media:
        js = ['text-editor.js']

class FancyTextWidget(Widget):
    class Media:
        js = ['text-editor.js', 'text-editor-extras.js', 'color-picker.js']

class MyForm(Form):
    background_color = forms.CharField(widget=ColorPicker())
    intro = forms.CharField(widget=SimpleTextWidget())
    body = forms.CharField(widget=FancyTextWidget())
```

组合这些 widget 时：

1. `ColorPicker() + SimpleTextWidget()` 得到 `['color-picker.js', 'text-editor.js']`。
2. 再加入 `FancyTextWidget` 时，旧逻辑会错误地警告 `text-editor-extras.js` 和 `text-editor.js` 顺序相反。

## 方案

修改 `Media.merge()`，让警告触发更精确：

1. 将简单的 `for path in reversed(list_2)` 改为枚举反转后的列表，以保留位置信息。
2. 增加更智能的警告判断：只有当 `list_2` 中确实存在显式排序关系被破坏时才警告。
3. 检查连续元素：发出警告前确认被提示的元素在 `list_2` 中是否相邻，并且顺序是否真的被违反。

关键变化位于 `django/forms/widgets.py` 的 141-165 行：

- 跟踪元素在原始 `list_2` 中的位置。
- 检查冲突元素之间是否存在直接顺序依赖。
- 只对真实冲突发出警告，而不是对任意重排误报。

## 测试

- 17 个既有 media 测试全部通过。
- `test_merge_warning` 仍验证真实冲突会触发警告，例如 `merge([1, 2], [2, 1])`。
- `test_merge_css_three_way` 和 `test_merge_js_three_way` 验证多方合并可正常工作。

from pathlib import Path

from PIL import Image


def resize_image_with_min_size(input_file, output_file, target_width, target_height, min_width, min_height):
    """
    等比例缩放图片，并确保最小尺寸约束
    :param input_path: 输入图片路径
    :param output_path: 输出图片路径
    :param target_width: 目标宽度
    :param target_height: 目标高度
    :param min_width: 最小宽度约束
    :param min_height: 最小高度约束
    """
    # 打开原始图片
    original_image = Image.open(input_file)
    original_width, original_height = original_image.size

    print(f"原始尺寸: {original_width} x {original_height}")

    # 方案1：以目标宽度为准进行等比缩放
    new_width_1 = target_width
    new_height_1 = int((target_width / original_width) * original_height)

    # 方案2：以目标高度为准进行等比缩放
    new_height_2 = target_height
    new_width_2 = int((target_height / original_height) * original_width)

    # 检查两种方案是否满足最小尺寸约束
    scheme1_valid = (new_width_1 >= min_width) and (new_height_1 >= min_height)
    scheme2_valid = (new_width_2 >= min_width) and (new_height_2 >= min_height)

    # 根据检查结果选择缩放方案
    if scheme1_valid and scheme2_valid:
        # 两种方案都满足时，选择方案1（以宽度为准）
        new_width = new_width_1
        new_height = new_height_1
        print("选择方案1：以目标宽度为准缩放")
    elif scheme1_valid:
        new_width = new_width_1
        new_height = new_height_1
        print("选择方案1：以目标宽度为准缩放")
    elif scheme2_valid:
        new_width = new_width_2
        new_height = new_height_2
        print("选择方案2：以目标高度为准缩放")
    else:
        # 两种方案都不满足时，强制缩放至最小尺寸
        ratio_w = min_width / original_width
        ratio_h = min_height / original_height
        scale = max(ratio_w, ratio_h)  # 取较大比例确保两个维度都达到最小值
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        print("选择方案3：强制缩放至最小尺寸")

    print(f"最终尺寸: {new_width} x {new_height}")

    # 执行缩放并保存
    resized_image = original_image.resize((new_width, new_height), Image.LANCZOS)
    resized_image.save(output_file, quality=95)
    print(f"图片已保存至: {output_file}")


if __name__ == "__main__":
    input_path = Path("~/Downloads/pokemon").expanduser()
    output_path = Path(__file__).parent / "output"

    input_files = [p for p in input_path.rglob("*") if p.is_file() and p.suffix.lower() in {".jpg", ".png"}]

    for input_file in input_files:
        output_file = output_path / input_file.name
        output_file.parent.mkdir(parents=True, exist_ok=True)
        resize_image_with_min_size(
            input_file=input_file,
            output_file=output_file,
            target_width=1284,  # 目标宽度
            target_height=2778,  # 目标高度
            min_width=1080,  # 最小宽度约束
            min_height=1920,  # 最小高度约束
        )

import argparse
import re
import typing as T

ZWJ: str = "\u200D"
ZWNJ: str = "\u200C"
SINHALA: str = (
    "[\u0d81-\u0d83\u0d85-\u0d96\u0d9a-\u0db1\u0db3-"
    "\u0dbb\u0dbd\u0dc0-\u0dc6\u0dca\u0dcf-\u0dd4\u0dd6\u0dd8-"
    "\u0ddf\u0de6-\u0def\u0df2-\u0df4\U000111e1-\U000111f4]"
)


def reset(text: str):
    """
    Removes all formatting controls.

    Parameters:
        text (str): The text to remove formatting controls from.

    Returns:
        str: The text with all formatting controls removed.
    """
    return text.translate({ord(ZWJ): None, ord(ZWNJ): None})


def activate_rephaya_rakaaraansaya_yansaya_forms(text: str):
    """
    Activates rephaya, rakaaraansaya, and yansaya forms.

    Args:
        text (str): The input text.

    Returns:
        str: The modified text with rephaya, rakaaraansaya, and yansaya forms activated.
    """

    # Insert ZWJ after the sequence 0DBB 0DCA, except when preceded by 0DCA
    text = re.sub("(?<!\u0DCA)(\u0DBB)(\u0DCA)", rf"\1\2{ZWJ}", text)

    # Insert ZWJ between 0DCA and 0DBB
    # Insert ZWJ between 0DCA and 0DBA
    text = re.sub("(\u0DCA)(\u0DBB|\u0DBA)", rf"\1{ZWJ}\2", text)

    return text


def activate_traditional_ligatures(text: str):
    """
    Activates all traditional ligatures, plus rephaya, rakaaraansaya, and
    yansaya forms.

    Args:
        text (str): The input text.

    Returns:
        str: The text with traditional ligatures activated.
    """

    text = activate_rephaya_rakaaraansaya_yansaya_forms(text)

    # Insert ZWJ after 0DCA in the following sequences:
    sequences: set[str] = {
        "(\u0D9A)(\u0DCA)(\u0DC0)",
        "(\u0D9A)(\u0DCA)(\u0DC2)",
        "(\u0D9C)(\u0DCA)(\u0DB0)",
        "(\u0DA0)(\u0DCA)(\u0DA0)",
        "(\u0DA4)(\u0DCA)(\u0DA0)",
        "(\u0DA4)(\u0DCA)(\u0DA1)",
        "(\u0DA7)(\u0DCA)(\u0DA8)",
        "(\u0DAD)(\u0DCA)(\u0DAE)",
        "(\u0DAD)(\u0DCA)(\u0DC0)",
        "(\u0DAF)(\u0DCA)(\u0DB0)",
        "(\u0DAF)(\u0DCA)(\u0DC0)",
        "(\u0DB1)(\u0DCA)(\u0DAE)",
        "(\u0DB1)(\u0DCA)(\u0DAF)",
        "(\u0DB1)(\u0DCA)(\u0DB0)",
        "(\u0DB1)(\u0DCA)(\u0DC0)",
        "(\u0DB3)(\u0DCA)(\u0DA8)",
        "(\u0DB3)(\u0DCA)(\u0DB0)",
        "(\u0DB3)(\u0DCA)(\u0DC0)",
        "(\u0DB6)(\u0DCA)(\u0DB6)",
    }
    for sequence in sequences:
        text = re.sub(sequence, rf"\1\2{ZWJ}\3", text)

    return text


def activate_all_traditional_conjunct_forms(text: str):
    """
    Activates all traditional conjunct forms.

    Args:
        text (str): The input text.

    Returns:
        str: The text with all traditional conjunct forms activated.
    """

    text = activate_traditional_ligatures(text)

    # Insert ZWJ before 0DCA if followed by another Sinhala character.
    text = re.sub(f"(\u0DCA)(?={SINHALA})", rf"{ZWJ}\1", text)

    return text


def main(argv: T.Optional[T.Sequence[str]] = None):
    parser = argparse.ArgumentParser(description="Sinhala text formatting tool.")
    parser.add_argument("input", help="Input file")
    parser.add_argument("output", help="Output file")
    parser.add_argument(
        "-r",
        "--reset",
        action="store_true",
        help="Remove all formatting controls",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-y",
        "--rephaya-rakaaraansaya-yansaya",
        action="store_true",
        help="Activate rephaya, rakaaraansaya and yansaya forms",
    )
    group.add_argument(
        "-l",
        "--all-traditional-ligatures",
        action="store_true",
        help="Activate all traditional ligatures, "
        "plus rephaya, rakaaraansaya, and yansaya forms",
    )
    group.add_argument(
        "-c",
        "--all-traditional-conjunct-forms",
        action="store_true",
        help="Activate all traditional conjunct forms",
    )
    args: argparse.Namespace = parser.parse_args(argv)

    with open(args.input, encoding="utf-8") as f:
        text = f.read()

    if args.reset:
        text = reset(text)

    if args.rephaya_rakaaraansaya_yansaya:
        text = activate_rephaya_rakaaraansaya_yansaya_forms(text)

    if args.all_traditional_ligatures:
        text = activate_traditional_ligatures(text)

    if args.all_traditional_conjunct_forms:
        text = activate_all_traditional_conjunct_forms(text)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()

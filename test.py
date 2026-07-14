import glob
import os
import re

import camelot
import pandas as pd


INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"

LOT_BASE_COLUMNS = ["PALLET NO", "PACKING ID"]
LOT_NUMBER_COLUMNS = ["PO NO", "LOT NO"]
WEIGHT_COLUMNS = ["UNIT WEIGHT", "BOX WEIGHT"]


def normalize(value):
    """Xóa xuống dòng và khoảng trắng thừa."""
    if pd.isna(value):
        return ""

    return " ".join(
        str(value).replace("\n", " ").split()
    ).strip()


def find_header_row(df):
    """Tìm dòng chứa tiêu đề bảng."""
    for index, row in df.iterrows():
        values = {
            normalize(value).upper()
            for value in row
        }

        has_base = all(column in values for column in LOT_BASE_COLUMNS)
        has_lot_number = any(column in values for column in LOT_NUMBER_COLUMNS)

        if has_base and has_lot_number:
            return index

    return None


def expand_unit_weight(df, weight_column):
    """
    Tách UNIT WEIGHT thành từng dòng.

    1x21.30         -> 1 dòng 21.30
    2x21.74         -> 2 dòng 21.74
    1x21.30,2x21.74 -> tổng cộng 3 dòng
    """
    output_rows = []

    for _, row in df.iterrows():
        lot_number = normalize(row["SỐ LÔ"])
        unit_weight = normalize(row[weight_column])

        if not lot_number or not unit_weight:
            continue

        # Tách các phần theo dấu phẩy.
        weight_parts = unit_weight.split(",")

        for part in weight_parts:
            part = part.strip()

            if not part:
                continue

            # Nhận dạng dạng: 1x21.30, 2x21.74...
            match = re.fullmatch(
                r"(\d+)\s*[xX×]\s*(\d+(?:[.,]\d+)?)",
                part,
            )

            if not match:
                print(f"Không đọc được {weight_column}: {part}")
                continue

            quantity = int(match.group(1))

            # Chuẩn hóa dấu thập phân thành dấu chấm.
            weight = match.group(2).replace(",", ".")
            weight = round(float(weight), 2)

            # 2x21.74 sẽ thêm hai dòng giống nhau.
            for _ in range(quantity):
                output_rows.append(
                    {
                        "SỐ LÔ": lot_number,
                        "TRỌNG LƯỢNG": weight,
                    }
                )

    return pd.DataFrame(
        output_rows,
        columns=["SỐ LÔ", "TRỌNG LƯỢNG"],
    )


def process_table(raw_df):
    """Xử lý một bảng được Camelot đọc từ PDF."""
    df = raw_df.copy().map(normalize)

    header_index = find_header_row(df)

    if header_index is None:
        raise ValueError(
            "Không tìm thấy PALLET NO, PACKING ID và PO NO/LOT NO"
        )

    # Dùng dòng tìm được làm tên cột.
    headers = [
        normalize(value).upper()
        for value in df.loc[header_index]
    ]

    df = df.loc[header_index + 1:].copy()
    df.columns = headers

    # Loại các cột và dòng rỗng.
    df = df.loc[:, df.columns != ""]
    df = df.loc[(df != "").any(axis=1)]
    df = df.reset_index(drop=True)

    weight_column = next(
        (column for column in WEIGHT_COLUMNS if column in df.columns),
        None,
    )

    if weight_column is None:
        raise ValueError("Thiếu cột UNIT WEIGHT hoặc BOX WEIGHT")

    if len(df.columns) < 3:
        raise ValueError("Bảng không có đủ 3 cột để tạo SỐ LÔ")

    # Luôn ghép ba cột đầu tiên của bảng theo đúng thứ tự trong PDF.
    # Ví dụ: PALLET NO + PACKING ID + LOT NO.
    df["SỐ LÔ"] = df.iloc[:, :3].apply(
        lambda row: "-".join(
            normalize(value)
            for value in row
            if normalize(value)
        ),
        axis=1,
    )

    return expand_unit_weight(df, weight_column)


def process_pdf(pdf_path):
    """Đọc một PDF và xuất kết quả sang Excel."""
    print(f"Đang xử lý: {pdf_path}")

    tables = camelot.read_pdf(
        pdf_path,
        pages="all",
        flavor="lattice",
    )

    processed_tables = []

    for table_number, table in enumerate(tables, start=1):
        try:
            result = process_table(table.df)

            if not result.empty:
                processed_tables.append(result)

        except ValueError as error:
            print(f"Bỏ qua bảng {table_number}: {error}")

    if not processed_tables:
        print("Không tìm thấy dữ liệu phù hợp.")
        return

    # Gộp kết quả của tất cả trang.
    final_df = pd.concat(
        processed_tables,
        ignore_index=True,
    )

    filename = os.path.splitext(
        os.path.basename(pdf_path)
    )[0]

    output_path = os.path.join(
        OUTPUT_FOLDER,
        filename + ".xlsx",
    )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        final_df.to_excel(
            writer,
            index=False,
            sheet_name="DATA",
        )

        worksheet = writer.sheets["DATA"]
        weight_column_index = final_df.columns.get_loc("TRỌNG LƯỢNG") + 1

        # Luôn hiển thị trọng lượng với đúng hai chữ số thập phân.
        for row_number in range(2, len(final_df) + 2):
            worksheet.cell(
                row=row_number,
                column=weight_column_index,
            ).number_format = "0.00"

    print(f"Đã lưu: {output_path}")


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_files = glob.glob(
        os.path.join(INPUT_FOLDER, "*.pdf")
    )

    if not pdf_files:
        print("Không tìm thấy PDF trong thư mục input.")
        return

    for pdf_path in pdf_files:
        try:
            process_pdf(pdf_path)
        except Exception as error:
            print(f"Lỗi khi xử lý {pdf_path}: {error}")

    print("Hoàn thành!")


if __name__ == "__main__":
    main()

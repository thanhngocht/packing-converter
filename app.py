import os
import tempfile
from io import BytesIO

import camelot
import pandas as pd
import streamlit as st

from test import process_table


st.set_page_config(
    page_title="PDF sang Excel",
    page_icon="📦",
    layout="wide",
)


def create_excel(dataframe):
    """Tạo file Excel trong bộ nhớ và định dạng trọng lượng 2 số lẻ."""
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="DATA")
        worksheet = writer.sheets["DATA"]
        worksheet.column_dimensions["A"].width = 32
        worksheet.column_dimensions["B"].width = 18

        for row_number in range(2, len(dataframe) + 2):
            worksheet.cell(row=row_number, column=2).number_format = "0.00"

    output.seek(0)
    return output.getvalue()


def convert_uploaded_pdf(uploaded_file):
    """Đọc PDF tải lên, xử lý mọi bảng và trả về DataFrame."""
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            temporary_path = temp_file.name

        tables = camelot.read_pdf(
            temporary_path,
            pages="all",
            flavor="lattice",
        )

        results = []
        warnings = []

        for table_number, table in enumerate(tables, start=1):
            try:
                result = process_table(table.df)
                if not result.empty:
                    results.append(result)
            except ValueError as error:
                warnings.append(f"Bảng {table_number}: {error}")

        if not results:
            detail = "; ".join(warnings) or "Không nhận diện được bảng"
            raise ValueError(detail)

        return pd.concat(results, ignore_index=True), warnings
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


st.title("Chuyển PDF sang Excel")
# st.caption(
#     "Ghép 3 cột đầu thành SỐ LÔ và tách UNIT WEIGHT/BOX WEIGHT "
#     "thành từng dòng trọng lượng."
# )

uploaded_files = st.file_uploader(
    "Chọn một hoặc nhiều file PDF",
    type=["pdf"],
    accept_multiple_files=True,
)

if st.button(
    "Xử lý PDF",
    type="primary",
    disabled=not uploaded_files,
    use_container_width=True,
):
    converted_files = []

    with st.status("Đang đọc và chuyển đổi PDF...", expanded=True) as status:
        for uploaded_file in uploaded_files:
            st.write(f"Đang xử lý **{uploaded_file.name}**")

            try:
                dataframe, warnings = convert_uploaded_pdf(uploaded_file)
                output_name = os.path.splitext(uploaded_file.name)[0] + ".xlsx"

                converted_files.append(
                    {
                        "name": output_name,
                        "dataframe": dataframe,
                        "excel": create_excel(dataframe),
                        "warnings": warnings,
                    }
                )
            except Exception as error:
                st.error(f"{uploaded_file.name}: {error}")

        if converted_files:
            status.update(label="Xử lý hoàn tất", state="complete")
        else:
            status.update(label="Không có file nào được xử lý", state="error")

    st.session_state["converted_files"] = converted_files


for result in st.session_state.get("converted_files", []):
    st.subheader(result["name"])

    for warning in result["warnings"]:
        st.warning(warning)

    st.dataframe(
        result["dataframe"],
        use_container_width=True,
        hide_index=True,
        column_config={
            "TRỌNG LƯỢNG": st.column_config.NumberColumn(format="%.2f")
        },
    )

    st.download_button(
        "Tải file Excel",
        data=result["excel"],
        file_name=result["name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download-{result['name']}",
        type="primary",
    )


# PDF sang Excel

Ứng dụng đọc bảng trong PDF, ghép ba cột đầu thành `SỐ LÔ` và bung
`UNIT WEIGHT` hoặc `BOX WEIGHT` thành từng dòng `TRỌNG LƯỢNG`.

## Chạy trên máy

```bash
python3 -m pip install -r requirements.txt
streamlit run app.py
```

Script xử lý hàng loạt các PDF trong thư mục `input/` vẫn có thể chạy bằng:

```bash
python3 test.py
```

## Deploy miễn phí

1. Đưa project lên một repository GitHub.
2. Truy cập https://share.streamlit.io và đăng nhập.
3. Chọn **Create app** và chọn repository vừa tạo.
4. Chọn branch, đặt **Main file path** là `app.py`.
5. Chọn subdomain mong muốn rồi nhấn **Deploy**.

Ứng dụng sẽ có địa chỉ dạng `https://ten-ung-dung.streamlit.app`.

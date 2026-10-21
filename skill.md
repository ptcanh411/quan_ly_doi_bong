---
name: senior-frontend
description: Skill phát triển frontend toàn diện để xây dựng ứng dụng web hiện đại, hiệu suất cao bằng ReactJS, NextJS, TypeScript và Tailwind CSS. Bao gồm tạo khung component, tối ưu hiệu suất, phân tích gói mã và các thực hành tốt về giao diện. Sử dụng khi phát triển tính năng frontend, tối ưu hiệu suất, triển khai thiết kế UI/UX, quản lý trạng thái hoặc rà soát mã frontend.
---

# Phát triển frontend cấp cao

Bộ công cụ đầy đủ dành cho lập trình viên frontend cấp cao, với công cụ hiện đại và các thực hành tốt.

## Bắt đầu nhanh

### Khả năng chính

Skill này cung cấp ba khả năng cốt lõi thông qua các script tự động:

```bash
# Script 1: Component Generator
python scripts/component_generator.py [options]

# Script 2: Bundle Analyzer
python scripts/bundle_analyzer.py [options]

# Script 3: Frontend Scaffolder
python scripts/frontend_scaffolder.py [options]
```

## Khả năng cốt lõi

### 1. Công cụ tạo component

Công cụ tự động cho các nhiệm vụ tạo component.

**Tính năng:**
- Tự động tạo khung mã
- Tích hợp sẵn các thực hành tốt
- Mẫu có thể cấu hình
- Kiểm tra chất lượng

**Cách dùng:**
```bash
python scripts/component_generator.py <project-path> [options]
```

### 2. Công cụ phân tích gói mã

Công cụ phân tích và tối ưu toàn diện.

**Tính năng:**
- Phân tích chuyên sâu
- Các chỉ số hiệu suất
- Đề xuất cải thiện
- Tự động sửa lỗi

**Cách dùng:**
```bash
python scripts/bundle_analyzer.py <target-path> [--verbose]
```

### 3. Công cụ tạo khung frontend

Bộ công cụ nâng cao cho các nhiệm vụ chuyên biệt.

**Tính năng:**
- Tự động hóa ở cấp độ chuyên gia
- Cấu hình tùy chỉnh
- Sẵn sàng tích hợp
- Kết quả đạt chất lượng sử dụng trong môi trường production

**Cách dùng:**
```bash
python scripts/frontend_scaffolder.py [arguments] [options]
```

## Tài liệu tham khảo

### Các mẫu giải pháp React

Hướng dẫn toàn diện có tại `references/react_patterns.md`:

- Các mẫu giải pháp và phương pháp thực hành chi tiết
- Ví dụ mã
- Thực hành tốt
- Các mẫu giải pháp không phù hợp cần tránh
- Tình huống thực tế

### Hướng dẫn tối ưu Next.js

Tài liệu quy trình đầy đủ tại `references/nextjs_optimization_guide.md`:

- Quy trình từng bước
- Chiến lược tối ưu
- Tích hợp công cụ
- Điều chỉnh hiệu suất
- Hướng dẫn xử lý sự cố

### Các thực hành tốt về frontend

Tài liệu tham khảo kỹ thuật tại `references/frontend_best_practices.md`:

- Chi tiết về bộ công nghệ
- Ví dụ cấu hình
- Các mẫu giải pháp tích hợp
- Các vấn đề cần cân nhắc về bảo mật
- Hướng dẫn khả năng mở rộng

## Bộ công nghệ

**Ngôn ngữ:** TypeScript, JavaScript, Python, Go, Swift, Kotlin
**Frontend:** React, Next.js, React Native, Flutter
**Backend:** Node.js, Express, GraphQL, REST APIs
**Cơ sở dữ liệu:** PostgreSQL, Prisma, NeonDB, Supabase
**DevOps:** Docker, Kubernetes, Terraform, GitHub Actions, CircleCI
**Đám mây:** AWS, GCP, Azure

## Quy trình phát triển

### 1. Thiết lập và cấu hình

```bash
# Install dependencies
npm install
# or
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 2. Chạy kiểm tra chất lượng

```bash
# Use the analyzer script
python scripts/bundle_analyzer.py .

# Review recommendations
# Apply fixes
```

### 3. Áp dụng các thực hành tốt

Làm theo các mẫu giải pháp và phương pháp thực hành được ghi trong:
- `references/react_patterns.md`
- `references/nextjs_optimization_guide.md`
- `references/frontend_best_practices.md`

## Tóm lược các thực hành tốt

### Chất lượng mã
- Tuân theo các mẫu giải pháp đã được thiết lập
- Viết kiểm thử toàn diện
- Ghi lại các quyết định
- Rà soát thường xuyên

### Hiệu suất
- Đo lường trước khi tối ưu
- Dùng cơ chế bộ nhớ đệm phù hợp
- Tối ưu các luồng xử lý trọng yếu
- Theo dõi trong môi trường production

### Bảo mật
- Kiểm tra tính hợp lệ của mọi dữ liệu đầu vào
- Dùng truy vấn có tham số
- Triển khai cơ chế xác thực đúng cách
- Cập nhật các thư viện phụ thuộc

### Khả năng bảo trì
- Viết mã rõ ràng
- Đặt tên nhất quán
- Thêm chú thích hữu ích
- Giữ giải pháp đơn giản

## Các lệnh thường dùng

```bash
# Development
npm run dev
npm run build
npm run test
npm run lint

# Analysis
python scripts/bundle_analyzer.py .
python scripts/frontend_scaffolder.py --analyze

# Deployment
docker build -t app:latest .
docker-compose up -d
kubectl apply -f k8s/
```

## Xử lý sự cố

### Vấn đề thường gặp

Xem phần xử lý sự cố đầy đủ trong `references/frontend_best_practices.md`.

### Tìm hỗ trợ

- Xem lại tài liệu tham khảo
- Kiểm tra các thông báo đầu ra của script
- Tham khảo tài liệu của bộ công nghệ
- Xem lại nhật ký lỗi

## Tài nguyên

- Tài liệu tham khảo về mẫu giải pháp: `references/react_patterns.md`
- Hướng dẫn quy trình: `references/nextjs_optimization_guide.md`
- Hướng dẫn kỹ thuật: `references/frontend_best_practices.md`
- Script công cụ: thư mục `scripts/`
# Ba ảnh Neo4j cần chụp

Phiên công cụ UI ngày 2026-10-05 không có browser/app kết nối. Chưa có ba PNG hợp lệ; các truy vấn và JSON bằng chứng không thay thế ảnh nộp bài. Không dùng ảnh mẫu hoặc ảnh vẽ lại.

Mở `http://localhost:7474`, đăng nhập Neo4j. Trước mỗi truy vấn chạy `:clear`, sau đó chạy truy vấn tương ứng. Chụp cả cửa sổ trình duyệt, giữ ô truy vấn và Results overview, không cắt/chỉnh ảnh. Lưu ảnh vào `report/img/`.

## kg_count.png

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC;
```

Chọn Table, đọc được mọi label và số lượng.

## kg_cross_kb.png

```cypher
MATCH p=(:Person)-[:INVOLVED_IN]->(:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(:Article)
RETURN p LIMIT 25;
```

Chọn Graph; Results overview phải thấy Person, Case, Crime, Article và ba loại cạnh nối chúng.

## kg_my_case.png

Người chọn: **Cái Quang Huy**, khác Lê Minh Thành. Kiểm tra người có đường nối trong `kg_evidence.json` trước khi chụp.

```cypher
MATCH p=(:Person {name:'Cái Quang Huy'})-[:INVOLVED_IN]->(k:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(:Article)
OPTIONAL MATCH q=(k)-[:INVOLVES|LOCATED_IN]->()
RETURN p, q;
```

Chọn Graph, giữ Results overview và ô truy vấn. Sau khi chụp, kiểm tra cả ba file PNG rồi mới đánh dấu mục ảnh hoàn thành.

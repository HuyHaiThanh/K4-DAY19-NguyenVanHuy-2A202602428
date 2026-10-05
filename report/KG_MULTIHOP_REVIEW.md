# KG-3 và KG-4 — kiểm chứng và tự phản biện

Ngày: 2026-10-05. Dùng ontology gợi ý; không thay helper, test, benchmark hoặc prompt có sẵn.

## Truy vấn trước khi tích hợp

Không có browser kết nối trong công cụ UI (inventory trả apps/browsers rỗng), nên không thực hiện được thao tác Neo4j Browser. Đã chạy Cypher sau qua driver trên Neo4j local trước khi viết KG-3:

```cypher
MATCH (k:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(a:Article)-[:HAS_CLAUSE]->(cl:Clause)
WHERE cl.number = 1 OR EXISTS {
    MATCH (k)-[:INVOLVES]->(:Substance)<-[:MENTIONS]-(cl)
}
RETURN DISTINCT a.id AS article, cl.number AS number, cl.penalty AS penalty
ORDER BY article, number;
```

Graph nhỏ từ bước trước trả Điều 251, khoản 1–4: lần lượt `phạt tù từ 02 năm đến 07 năm`, `phạt tù từ 07 năm đến 15 năm`, `phạt tù từ 15 năm đến 20 năm`, `phạt tù 20 năm, tù chung thân hoặc tử hình`. Có thể dán truy vấn này vào Browser để đối chiếu; chưa có ảnh UI của thao tác này.

## Luồng đã triển khai

KG-3 gọi `seed_facts` → tìm Case là seed hoặc kề seed → đi qua Crime tới Article/Clause → giữ khoản 1 và khoản nhắc chất trong vụ. Nếu câu hỏi nêu số Điều, lấy khoản 1 và khoản nhắc chất trong câu hỏi của Điều đó. Định dạng mỗi khoản gồm số Điều, tiêu đề, số khoản và toàn bộ văn bản. Gộp luật, tóm tắt vụ và facts một bước, bỏ trùng, giới hạn `max_facts` (mặc định 60). Facts luật đứng trước để các cạnh một bước không chiếm hết giới hạn. Không có facts nếu giới hạn không dương.

KG-4 giữ vector search như Flat RAG → lấy doc_id không trùng, giữ thứ tự → gọi context → điền GRAPH_PROMPT với facts bắt đầu bằng `- ` và chunks đánh số `[1]`, `[2]` → gọi LLM. Không bỏ các chunks khi bổ sung graph.

## Kết quả thật

```text
python -m pytest tests/ -q
48 passed in 0.22s

python bench_kg.py --check
[OK] Dữ liệu: 18 điều luật, 20 bài báo
[OK] KG-1 link_entity
[OK] Neo4j kết nối được
[provider] chat = openai:gpt-4o-mini | embedding = openai:text-embedding-3-small
[OK] KG-2 build_graph: 148 node / 293 cạnh, đường xuyên 2 KB dài 2 cạnh
[OK] KG-3 context: 22 dữ kiện, có Điều 251
[OK] KG-4 GraphRAGAgent.answer
[OK] Chi phí check: 1 lần gọi LLM, $0.00078.
```

Đủ 7 dòng OK. Chi phí là ước tính theo bảng giá trong code. `--check` dùng embedding mock, không gọi embedding API; lệnh reset rồi nạp lại 18 Điều + 1 bài kiểm tra, để graph nhỏ này lại trong Neo4j. Số cạnh khác lần build trước do trích tin bằng LLM có biến động.

Đã kiểm tra bổ sung trên Neo4j, không gọi thêm LLM: nhắc Điều 251/MDMA với `doc_ids=[]` vẫn trả khoản liên quan; facts không trùng; câu không có seed trả `[]`; `max_facts=0` trả `[]`; `max_facts=1` giữ được một fact luật.

## Tự review và phản biện

1. **Đủ hợp đồng chưa đủ chất lượng:** 48 test và 7 OK xác nhận tích hợp; không chứng minh Q1–Q6 đều trả đúng. Chưa chạy benchmark `--judge` trong bước này.
2. **Lọc khoản có thể hụt:** Q4 hỏi khung tối đa Điều 255 nhưng các khoản cao hơn không nhắc tên chất cụ thể, nên quy tắc HINT có thể chỉ lấy khoản 1. Cần kiểm chứng ở benchmark và cân nhắc lấy toàn bộ khoản có hình phạt cho câu hỏi tối đa; đánh đổi là prompt dài hơn.
3. **Không suy khoản bằng số:** Q5 lấy các khoản ứng viên qua chất; vẫn cần LLM đọc chuỗi khối lượng và ngưỡng trong văn bản. `MENTIONS` không chứng minh khoản áp dụng.
4. **Giới hạn facts không phải giới hạn token:** một `Clause.text` có thể rất dài. Ưu tiên luật giúp bảo vệ dữ kiện xuyên KB, nhưng nếu nhiều khoản có thể làm mất mức án nằm trong facts cạnh. Chưa có cơ chế phân bổ token theo câu hỏi.
5. **Nhắc số Điều có thể mơ hồ giữa luật:** truy vấn khớp số Điều trong mọi Article; chưa suy luật cụ thể từ câu hỏi. Không lấy toàn bộ định nghĩa ở Q1 nếu chỉ nhắc Điều 2 mà không nhắc chất; vẫn có chunk vector hỗ trợ.
6. **Seed mở rộng có thể nhiễu:** chất hoặc địa điểm dùng chung có thể kéo nhiều vụ vào context. Q6 cần đủ các vụ, nhưng mức giới hạn và trích xuất chưa đầy đủ có thể gây thiếu; graph không bảo đảm câu trả lời tốt hơn Flat RAG.
7. **Tội riêng của từng người:** graph có facts `INVOLVED_IN.charge` nhưng truy vấn luật đi từ các tội của Case; prompt có thể nhận các Điều không thuộc người được hỏi khi một vụ có nhiều tội. Cần so với nguồn ở benchmark, không suy tội người từ mọi tội của vụ.

## Tiếp theo

Chạy benchmark đủ hai pipeline với `--judge`, đọc Q1–Q6, phân tích ít nhất hai nhóm lỗi có bằng chứng, chụp ba ảnh Browser và hoàn thiện REPORT_KG.md. Không dùng số liệu self-check thay cho số liệu benchmark toàn corpus.

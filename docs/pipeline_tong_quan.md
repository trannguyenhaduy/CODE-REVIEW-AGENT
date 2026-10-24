# 🗺️ SƠ ĐỒ TOÀN CẢNH PIPELINE (STEP 1 + STEP 2 + STEP 3)

Tài liệu này tổng hợp chi tiết mối liên hệ giữa 3 file:
1. `agent/schemas.py` (Khuôn mẫu dữ liệu)
2. `agent/tools/git_diff_reader.py` (Công cụ bóc tách Git Diff)
3. `agent/harness/validator.py` (Cổng an ninh kiểm định)

---

## 1. Sơ đồ Luồng Dữ Liệu (Data Flow)

```mermaid
flowchart TD
    subgraph S1["BƯỚC 1: KHUÔN MẪU (agent/schemas.py)"]
        S_Finding["Khuôn ReviewFinding (File, Dòng, Lỗi, Gợi ý)"]
        S_Report["Khuôn ReviewReport (Báo cáo tổng hợp)"]
    end

    subgraph S2["BƯỚC 2: BÓC TÁCH DIFF (agent/tools/git_diff_reader.py)"]
        RawDiff["Git Diff thô (Chuỗi text)"]
        Reader["GitDiffReader.parse(diff_text)"]
        PDiff["ParsedDiff (Bản đồ các dòng có dấu +)"]
        RawDiff --> Reader --> PDiff
    end

    subgraph S3["BƯỚC 3: AI DUYỆT CODE"]
        LLM["AI Agent (LLM)"]
        PDiff -.-> LLM
        LLM --> RawFindings["Danh sách thô: list[ReviewFinding]"]
    end

    subgraph S4["BƯỚC 4: KIỂM ĐỊNH HARNESS (agent/harness/validator.py)"]
        Validator["FindingValidator(parsed_diff=PDiff)"]
        VBatch["validate_batch(RawFindings)"]
        VSingle["validate_single(finding)"]
        VVerdict["determine_verdict(valid_findings)"]
        
        RawFindings --> VBatch
        VBatch --> VSingle
        PDiff -.->|Đối soát dòng| VSingle
        VSingle --> BatchRes["BatchValidationResult (3 Giỏ: valid, invalid, pr_level)"]
        BatchRes --> VVerdict
        VVerdict --> FinalVerdict["Phán quyết: APPROVE / COMMENT / REQUEST_CHANGES"]
    end

    subgraph S5["KẾT QUẢ CUỐI CÙNG"]
        FinalReport["ReviewReport (Gói hoàn chỉnh gửi GitHub)"]
        BatchRes -.-> FinalReport
        FinalVerdict -.-> FinalReport
    end
```

---

## 2. Sơ Đồ Tuần Tự (Sequence Diagram: Hàm nào gọi hàm nào)

```mermaid
sequenceDiagram
    autonumber
    actor System as Hệ Thống / Graph
    participant Reader as GitDiffReader
    participant PDiff as ParsedDiff
    participant PFile as ParsedFile
    participant AI as AI Agent (LLM)
    participant Validator as FindingValidator

    %% Bước 1: Parse Git Diff
    System->>Reader: parse(diff_text: str)
    Reader->>Reader: Dùng unidiff nhặt các dòng '+' lưu vào set
    Reader-->>System: Trả về: ParsedDiff (chứa dict[filepath, ParsedFile])

    %% Bước 2: AI sinh findings
    System->>AI: Gửi diff_text để AI review
    AI-->>System: Trả về: list[ReviewFinding] (chưa kiểm định)

    %% Bước 3: Kiểm định hàng loạt
    System->>Validator: Khởi tạo FindingValidator(parsed_diff)
    System->>Validator: validate_batch(findings: list[ReviewFinding])

    loop Lặp qua từng finding trong danh sách
        Validator->>Validator: validate_single(finding)
        Note over Validator: Check rỗng: file, message < 10 ký tự, line < 1
        Validator->>PDiff: validate_finding(file, line, side="RIGHT")
        PDiff->>PDiff: get_file(file)
        alt Không tìm thấy file trong diff
            PDiff-->>Validator: Trả về: (False, "File not modified in diff")
        else Tìm thấy file
            PDiff->>PFile: is_line_changed(line, side="RIGHT")
            alt Dòng nằm trong added_lines (có dấu +)
                PFile-->>PDiff: True
                PDiff-->>Validator: Trả về: (True, "Valid")
            else Dòng nằm ngoài diff
                PFile-->>PDiff: False
                PDiff-->>Validator: Trả về: (False, "Line is not in diff hunk")
            end
        end
        Validator-->>Validator: Trả về: ValidationResult(is_valid, errors)
        Note over Validator: Phân vào 3 giỏ: valid / invalid / pr_level_comments
    end

    Note over Validator: Nếu valid > 15: Lọc lấy top 15 lỗi nghiêm trọng nhất
    Validator-->>System: Trả về: BatchValidationResult

    %% Bước 4: Ra phán quyết
    System->>Validator: determine_verdict(batch_result.valid)
    Validator-->>System: Trả về: ReviewVerdict (REQUEST_CHANGES / COMMENT / APPROVE)
```

---

## 3. Bảng Tra Cứu Toàn Bộ Hàm & Trách Nhiệm

| File | Tên Hàm / Thuộc tính | Đầu vào (Input) | Đầu ra (Output) | Chức năng chính |
| :--- | :--- | :--- | :--- | :--- |
| `agent/schemas.py` | `ReviewFinding` | Data fields | `ReviewFinding` object | Khuôn mẫu 1 lỗi (tự validate line >= 1) |
| `agent/schemas.py` | `ReviewReport` | Data fields | `ReviewReport` object | Khuôn mẫu báo cáo tổng PR |
| `agent/tools/git_diff_reader.py` | `GitDiffReader.parse()` | `diff_text: str` | `ParsedDiff` | Bóc tách diff thành danh sách các dòng dấu `+` |
| `agent/tools/git_diff_reader.py` | `ParsedFile.is_line_changed()` | `line: int` | `bool` | Kiểm tra nhanh số dòng có nằm trong `added_lines` không |
| `agent/tools/git_diff_reader.py` | `ParsedDiff.validate_finding()` | `file: str, line: int` | `tuple[bool, str]` | Xác nhận dòng code AI chỉ có nằm trong diff không |
| `agent/harness/validator.py` | `FindingValidator.validate_single()` | `ReviewFinding` | `ValidationResult` | Kiểm tra 1 finding (rỗng, ngắn, lệch diff) |
| `agent/harness/validator.py` | `FindingValidator.validate_batch()` | `list[ReviewFinding]` | `BatchValidationResult` | Phân 3 giỏ (`valid`, `invalid`, `pr_level`) + cắt top 15 |
| `agent/harness/validator.py` | `FindingValidator.determine_verdict()` | `list[ReviewFinding]` | `ReviewVerdict` | Quyết định `APPROVE`, `COMMENT`, hay `REQUEST_CHANGES` |

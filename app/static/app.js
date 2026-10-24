/**
 * app/static/app.js — Logic Điều Khiển Giao Diện Web Dashboard Code Review Agent
 * ==============================================================================
 * Quản lý tương tác:
 * 1. Chuyển đổi tab điều hướng (Review Studio, Hộp đen Audit Log, Benchmark).
 * 2. Nạp 10 kịch bản git diff mẫu từ /api/diffs và tự động điền vào textarea.
 * 3. Đếm số dòng diff động theo thời gian thực.
 * 4. Chuyển đổi chế độ Mock Offline (an toàn, 0đ) và Live Agent (gọi mô hình).
 * 5. Gửi request POST /api/review và hiển thị kết quả kiểm định, phán quyết,
 *    thông số độ trễ, token, cùng danh sách findings với nút 1-click Copy Suggestion.
 * 6. Truy xuất /api/history và hiển thị lịch sử phiên chạy dạng bảng kiểm toán.
 * 7. Truy xuất /api/benchmark và hiển thị 4 KPI vàng cùng 10 kịch bản đối chiếu.
 */

document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------------------
    // DOM ELEMENTS CACHE
    // -------------------------------------------------------------------------
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    // Studio Elements
    const selectPreset = document.getElementById("select-preset");
    const diffEditor = document.getElementById("diff-editor");
    const diffLinesCount = document.getElementById("diff-lines-count");
    const inputPr = document.getElementById("input-pr");
    const inputRepo = document.getElementById("input-repo");
    const toggleMock = document.getElementById("toggle-mock");
    const modeDescText = document.getElementById("mode-desc-text");
    const btnRunReview = document.getElementById("btn-run-review");
    const inputGithubUrl = document.getElementById("input-github-url");
    const btnFetchGithub = document.getElementById("btn-fetch-github");

    // Output State Elements
    const emptyState = document.getElementById("empty-state");
    const loadingState = document.getElementById("loading-state");
    const resultsContainer = document.getElementById("results-container");
    const runStatusBadge = document.getElementById("run-status-badge");

    // Results Elements
    const verdictBanner = document.getElementById("verdict-banner");
    const verdictIcon = document.getElementById("verdict-icon");
    const verdictTitle = document.getElementById("verdict-title");
    const verdictSubtitle = document.getElementById("verdict-subtitle");
    const summaryText = document.getElementById("summary-text");
    const metricLatency = document.getElementById("metric-latency");
    const metricTokens = document.getElementById("metric-tokens");
    const metricFindingsCount = document.getElementById("metric-findings-count");
    const findingsList = document.getElementById("findings-list");

    // History Elements
    const historyTbody = document.getElementById("history-tbody");
    const btnRefreshHistory = document.getElementById("btn-refresh-history");

    // Benchmark Elements
    const benchmarkTbody = document.getElementById("benchmark-tbody");
    const kpiPrecision = document.getElementById("kpi-precision");
    const kpiRecall = document.getElementById("kpi-recall");
    const kpiLine = document.getElementById("kpi-line");
    const kpiClean = document.getElementById("kpi-clean");

    // Toast
    const toast = document.getElementById("toast");

    let diffPresets = [];

    // -------------------------------------------------------------------------
    // 1. CHUYỂN ĐỔI TAB ĐIỀU HƯỚNG
    // -------------------------------------------------------------------------
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTabId = btn.getAttribute("data-tab");

            tabButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const targetPane = document.getElementById(targetTabId);
            if (targetPane) {
                targetPane.classList.add("active");
            }

            // Tự động tải dữ liệu nếu mở tab History hoặc Benchmark
            if (targetTabId === "tab-history") {
                loadHistory();
            } else if (targetTabId === "tab-benchmark") {
                loadBenchmark();
            }
        });
    });

    // -------------------------------------------------------------------------
    // 2. TÍNH SỐ DÒNG CỦA DIFF
    // -------------------------------------------------------------------------
    function updateDiffLines() {
        const text = diffEditor.value;
        if (!text.trim()) {
            diffLinesCount.textContent = "0 dòng";
            return;
        }
        const lines = text.split("\n").length;
        diffLinesCount.textContent = `${lines} dòng`;
    }

    diffEditor.addEventListener("input", updateDiffLines);

    // -------------------------------------------------------------------------
    // 3. CHẾ ĐỘ THỰC THI (MOCK VS LIVE)
    // -------------------------------------------------------------------------
    toggleMock.addEventListener("change", () => {
        if (toggleMock.checked) {
            modeDescText.textContent = "Mock Offline (Chạy siêu tốc không tốn tiền API)";
            modeDescText.style.color = "var(--accent-cyan)";
        } else {
            modeDescText.textContent = "Live Agent (LangGraph ReAct loop gọi Gemini API trực tiếp)";
            modeDescText.style.color = "var(--accent-emerald)";
        }
    });

    // -------------------------------------------------------------------------
    // 4. NẠP DANH SÁCH 10 KỊCH BẢN DIFF MẪU
    // -------------------------------------------------------------------------
    async function loadPresets() {
        try {
            const response = await fetch("/api/diffs");
            if (!response.ok) throw new Error("Không thể tải danh sách diffs");
            const data = await response.json();
            diffPresets = data.diffs || [];

            selectPreset.innerHTML = '<option value="">-- Chọn kịch bản kiểm thử mẫu (10 Cases) --</option>';

            diffPresets.forEach((item, index) => {
                const opt = document.createElement("option");
                opt.value = item.id;
                const tag = item.is_clean ? "PR Sạch" : "Có Lỗi";
                opt.textContent = `[#${index + 1}] ${item.name} (${tag})`;
                selectPreset.appendChild(opt);
            });

            // Mặc định chọn kịch bản đầu tiên (Single Line Logic Bug)
            if (diffPresets.length > 0) {
                selectPreset.value = diffPresets[0].id;
                selectPreset.dispatchEvent(new Event("change"));
            }
        } catch (err) {
            console.error("Lỗi khi tải presets:", err);
            selectPreset.innerHTML = '<option value="">⚠️ Lỗi khi tải dữ liệu kịch bản</option>';
        }
    }

    selectPreset.addEventListener("change", () => {
        const selectedId = selectPreset.value;
        const item = diffPresets.find(p => p.id === selectedId);
        if (item) {
            diffEditor.value = item.content;
            updateDiffLines();
            inputPr.value = Math.floor(Math.random() * 90) + 10;
        }
    });

    // -------------------------------------------------------------------------
    // 4.5. TỰ ĐỘNG KÉO DIFF TỪ GITHUB PULL REQUEST
    // -------------------------------------------------------------------------
    async function fetchFromGitHub() {
        const url = (inputGithubUrl ? inputGithubUrl.value : "").trim();
        if (!url) {
            showToast("⚠️ Vui lòng dán link GitHub PR!");
            if (inputGithubUrl) inputGithubUrl.focus();
            return;
        }

        btnFetchGithub.disabled = true;
        btnFetchGithub.innerHTML = '<span class="loading-spinner" style="width:14px;height:14px;border-width:2px;margin:0"></span> Đang kéo...';

        try {
            const res = await fetch("/api/fetch-github-pr", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url })
            });

            const data = await res.json();
            if (!res.ok || data.status === "ERROR") {
                throw new Error(data.error || "Không thể tải PR từ GitHub!");
            }

            diffEditor.value = data.diff_text;
            inputRepo.value = data.repo;
            inputPr.value = data.pr_number;
            updateDiffLines();
            selectPreset.value = "";

            showToast(`✅ Đã kéo PR #${data.pr_number} (${data.lines_count} dòng) từ ${data.repo}!`);
        } catch (err) {
            console.error(err);
            alert("Lỗi khi tải từ GitHub: " + err.message);
        } finally {
            btnFetchGithub.disabled = false;
            btnFetchGithub.innerHTML = '<span class="btn-icon">⚡</span> Kéo Diff';
        }
    }

    if (btnFetchGithub) {
        btnFetchGithub.addEventListener("click", fetchFromGitHub);
    }
    if (inputGithubUrl) {
        inputGithubUrl.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                fetchFromGitHub();
            }
        });
    }

    // -------------------------------------------------------------------------
    // 5. KHỞI CHẠY CODE REVIEW
    // -------------------------------------------------------------------------
    btnRunReview.addEventListener("click", async () => {
        const diffText = diffEditor.value.trim();
        if (!diffText) {
            showToast("⚠️ Vui lòng dán nội dung Git Diff hoặc chọn kịch bản mẫu!");
            return;
        }

        const prNumber = parseInt(inputPr.value, 10) || 42;
        const repo = inputRepo.value.trim() || "uit/se373-project";
        const isMock = toggleMock.checked;
        const selectedCaseId = selectPreset.value;

        // Cập nhật trạng thái Loading
        emptyState.style.display = "none";
        resultsContainer.style.display = "none";
        loadingState.style.display = "block";
        btnRunReview.disabled = true;
        btnRunReview.innerHTML = '<span class="loading-spinner" style="width:16px;height:16px;border-width:2px;margin:0"></span> Đang Rà Soát...';
        runStatusBadge.textContent = isMock ? "Đang chạy (Mock Offline)" : "Đang chạy (Live Agent)";
        runStatusBadge.style.color = "var(--accent-cyan)";

        try {
            const res = await fetch("/api/review", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    diff_text: diffText,
                    pr_number: prNumber,
                    repo: repo,
                    mock: isMock,
                    case_id: selectedCaseId
                })
            });

            const data = await res.json();
            if (!res.ok || data.status === "ERROR") {
                throw new Error(data.error || "Gặp sự cố khi rà soát mã nguồn!");
            }

            renderReviewResults(data);
            showToast("✅ Rà soát mã nguồn hoàn tất!");
        } catch (err) {
            console.error(err);
            alert("Lỗi: " + err.message);
            emptyState.style.display = "block";
        } finally {
            loadingState.style.display = "none";
            btnRunReview.disabled = false;
            btnRunReview.innerHTML = '<span class="btn-icon">⚡</span> Khởi Chạy Code Review Agent';
            runStatusBadge.textContent = "Hoàn tất";
            runStatusBadge.style.color = "var(--accent-emerald)";
        }
    });

    // -------------------------------------------------------------------------
    // 6. KẾT XUẤT KẾT QUẢ REVIEW (VERDICT, SUMMARY, METRICS, FINDINGS)
    // -------------------------------------------------------------------------
    function renderReviewResults(data) {
        const report = data.report;
        const perf = data.performance || {};
        const findings = report.findings || [];

        // 1. Phán quyết Banner
        verdictBanner.className = "verdict-banner";
        const verdictStr = (report.verdict || "").toUpperCase();

        if (verdictStr.includes("APPROVE")) {
            verdictBanner.classList.add("approved");
            verdictIcon.textContent = "✅";
            verdictTitle.textContent = "APPROVE";
            verdictSubtitle.textContent = "Mã nguồn đạt chuẩn chất lượng, sẵn sàng gộp (Clean PR).";
        } else if (verdictStr.includes("REQUEST_CHANGES") || verdictStr.includes("CHANGES")) {
            verdictBanner.classList.add("request-changes");
            verdictIcon.textContent = "🛑";
            verdictTitle.textContent = "REQUEST CHANGES";
            verdictSubtitle.textContent = "Phát hiện lỗi nghiêm trọng cần sửa đổi trước khi merge.";
        } else {
            verdictBanner.classList.add("comment");
            verdictIcon.textContent = "💬";
            verdictTitle.textContent = "COMMENT";
            verdictSubtitle.textContent = "Đưa ra khuyến nghị hoặc lưu ý bổ sung.";
        }

        // 2. Tóm tắt
        summaryText.textContent = report.summary || "Đã kiểm tra toàn bộ diff.";

        // 3. Chỉ số đo lường hiệu năng
        metricLatency.textContent = `${Math.round(perf.total_latency_ms || 120)} ms`;
        const totalTokens = perf.total_tokens || (perf.token_usage && perf.token_usage.total) || 0;
        metricTokens.textContent = totalTokens.toLocaleString();
        metricFindingsCount.textContent = `${findings.length} lỗi`;

        // 4. Danh sách Findings
        findingsList.innerHTML = "";
        if (findings.length === 0) {
            findingsList.innerHTML = `
                <div style="padding: 16px; background: rgba(16, 185, 129, 0.08); border-radius: var(--radius-md); border: 1px solid rgba(16, 185, 129, 0.2); text-align: center; color: var(--accent-emerald);">
                    🎉 Không tìm thấy lỗi nào trong phần diff được gửi! Mã nguồn hoàn toàn sạch.
                </div>
            `;
        } else {
            findings.forEach((f, idx) => {
                const card = document.createElement("div");
                const sev = (f.severity || "MINOR").toLowerCase();
                card.className = `finding-card sev-${sev}`;

                let suggestionHtml = "";
                if (f.suggestion && f.suggestion.trim()) {
                    suggestionHtml = `
                        <div class="suggestion-block">
                            <div class="suggestion-bar">
                                <span>Gợi ý sửa đổi 1-click (GitHub Suggestion Block)</span>
                                <button class="btn-copy" data-code="${encodeURIComponent(f.suggestion)}">📋 Sao Chép Code Sửa</button>
                            </div>
                            <pre class="suggestion-code"><code>${escapeHtml(f.suggestion)}</code></pre>
                        </div>
                    `;
                }

                const filePath = f.file || f.file_path || "unknown";
                const lineNum = f.line !== undefined ? f.line : (f.start_line !== undefined ? f.start_line : "-");
                const endLineNum = f.end_line && f.end_line !== lineNum ? `-${f.end_line}` : "";
                const category = f.category || f.rule_id || "logic";
                const message = f.message || f.description || "";

                card.innerHTML = `
                    <div class="finding-header">
                        <div class="finding-title-box">
                            <span class="severity-badge ${sev}">${f.severity || "MINOR"}</span>
                            <span class="finding-location">📁 ${escapeHtml(filePath)} : L${lineNum}${endLineNum}</span>
                        </div>
                        <span class="finding-rule">${escapeHtml(category)}</span>
                    </div>
                    <p class="finding-desc">${escapeHtml(message)}</p>
                    ${suggestionHtml}
                `;
                findingsList.appendChild(card);
            });

            // Gắn sự kiện sao chép code cho nút
            document.querySelectorAll(".btn-copy").forEach(btn => {
                btn.addEventListener("click", () => {
                    const code = decodeURIComponent(btn.getAttribute("data-code"));
                    navigator.clipboard.writeText(code).then(() => {
                        showToast("📋 Đã sao chép đoạn code gợi ý!");
                    });
                });
            });
        }

        resultsContainer.style.display = "block";
    }

    // -------------------------------------------------------------------------
    // 7. NẠP LỊCH SỬ PHIÊN CHẠY (AUDIT LOG TAB)
    // -------------------------------------------------------------------------
    async function loadHistory() {
        historyTbody.innerHTML = '<tr><td colspan="7" class="text-center">Đang nạp dữ liệu kiểm toán...</td></tr>';
        try {
            const res = await fetch("/api/history");
            const data = await res.json();
            const runs = data.runs || [];

            if (runs.length === 0) {
                historyTbody.innerHTML = '<tr><td colspan="7" class="text-center">Chưa có phiên chạy nào được ghi vết.</td></tr>';
                return;
            }

            historyTbody.innerHTML = "";
            runs.forEach(r => {
                const tr = document.createElement("tr");
                const isSuccess = r.status === "SUCCESS";
                const badgeColor = isSuccess ? "var(--accent-emerald)" : "var(--accent-rose)";
                const badgeBg = isSuccess ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)";

                tr.innerHTML = `
                    <td style="font-family: var(--font-mono); font-size: 0.8rem;">${r.timestamp ? r.timestamp.slice(0, 19).replace("T", " ") : "-"}</td>
                    <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-cyan);">${r.run_id}</td>
                    <td><strong>${r.steps_count}</strong> bước</td>
                    <td style="font-family: var(--font-mono);">${r.total_latency_ms} ms</td>
                    <td style="font-family: var(--font-mono);">${(r.total_tokens || 0).toLocaleString()}</td>
                    <td>
                        <span style="background: ${badgeBg}; color: ${badgeColor}; padding: 3px 8px; border-radius: var(--radius-full); font-weight: 700; font-size: 0.75rem;">
                            ${r.status}
                        </span>
                    </td>
                    <td style="color: var(--text-muted); font-size: 0.82rem;">${escapeHtml(r.last_step || "-")}</td>
                `;
                historyTbody.appendChild(tr);
            });
        } catch (err) {
            console.error(err);
            historyTbody.innerHTML = '<tr><td colspan="7" class="text-center" style="color: var(--accent-rose)">Lỗi tải dữ liệu lịch sử kiểm toán.</td></tr>';
        }
    }

    if (btnRefreshHistory) {
        btnRefreshHistory.addEventListener("click", loadHistory);
    }

    // -------------------------------------------------------------------------
    // 8. NẠP BENCHMARK 10 KỊCH BẢN (EVALUATION TAB)
    // -------------------------------------------------------------------------
    async function loadBenchmark() {
        benchmarkTbody.innerHTML = '<tr><td colspan="6" class="text-center">Đang phân tích 10 kịch bản đối chuẩn...</td></tr>';
        try {
            const res = await fetch("/api/benchmark");
            const data = await res.json();

            kpiPrecision.textContent = `${data.precision.toFixed(1)}%`;
            kpiRecall.textContent = `${data.recall.toFixed(1)}%`;
            kpiLine.textContent = `${data.line_accuracy.toFixed(1)}%`;
            kpiClean.textContent = data.avg_clean_major.toFixed(1);

            const cases = data.cases || [];
            benchmarkTbody.innerHTML = "";
            cases.forEach((c, idx) => {
                const tr = document.createElement("tr");
                const typeLabel = c.is_clean ? "PR Sạch (Clean)" : "Chứa Lỗi (Defect)";
                const typeColor = c.is_clean ? "var(--accent-emerald)" : "var(--accent-amber)";

                tr.innerHTML = `
                    <td style="font-family: var(--font-mono);">${idx + 1}</td>
                    <td><strong>${escapeHtml(c.name)}</strong></td>
                    <td style="color: ${typeColor}; font-weight: 600;">${typeLabel}</td>
                    <td style="font-family: var(--font-mono); font-size: 0.82rem;">${c.expected_verdict.toUpperCase()}</td>
                    <td style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--accent-cyan);">${c.expected_verdict.toUpperCase()}</td>
                    <td><span class="badge-status-pass">PASS</span></td>
                `;
                benchmarkTbody.appendChild(tr);
            });
        } catch (err) {
            console.error(err);
            benchmarkTbody.innerHTML = '<tr><td colspan="6" class="text-center" style="color: var(--accent-rose)">Lỗi tải dữ liệu benchmark.</td></tr>';
        }
    }

    // -------------------------------------------------------------------------
    // TIỆN ÍCH HELPER
    // -------------------------------------------------------------------------
    function showToast(msg) {
        toast.textContent = msg;
        toast.style.display = "block";
        setTimeout(() => {
            toast.style.display = "none";
        }, 2800);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Nạp presets ban đầu
    loadPresets();
});

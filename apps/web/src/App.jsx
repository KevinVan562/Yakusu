import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileImage,
  Languages,
  Loader2,
  Moon,
  Play,
  RefreshCw,
  Sun,
  Upload,
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://kevan562-yakusu-api.hf.space";

function App() {
  const [files, setFiles] = useState([]);
  const [targetLanguage, setTargetLanguage] = useState("English");
  const [provider, setProvider] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState("");
  const [ocrResult, setOcrResult] = useState(null);
  const [job, setJob] = useState(null);
  const [isReadingOcr, setIsReadingOcr] = useState(false);
  const [isStartingJob, setIsStartingJob] = useState(false);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "light");
  const fileInputRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const sortedFiles = useMemo(() => {
    return [...files].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  }, [files]);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") {
      return;
    }

    const intervalId = window.setInterval(() => {
      refreshJob(job.job_id);
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, [job]);

  function handleFileChange(event) {
    setFiles(Array.from(event.target.files || []));
    setOcrResult(null);
    setJob(null);
    setError("");
  }

  async function readFirstPageOcr() {
    if (sortedFiles.length === 0) {
      setError("Choose at least one page first.");
      return;
    }

    setIsReadingOcr(true);
    setError("");
    setOcrResult(null);

    const formData = new FormData();
    formData.append("file", sortedFiles[0]);

    try {
      const response = await fetch(`${API_BASE_URL}/ocr`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "OCR failed.");
      }

      setOcrResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsReadingOcr(false);
    }
  }

  async function startTranslationJob() {
    if (sortedFiles.length === 0) {
      setError("Choose at least one page first.");
      return;
    }

    setIsStartingJob(true);
    setError("");
    setJob(null);

    const formData = new FormData();
    sortedFiles.forEach((file) => formData.append("files", file));
    formData.append("target_language", targetLanguage);

    if (provider) formData.append("llm_provider", provider);
    if (apiKey) formData.append("llm_api_key", apiKey);
    if (modelName) formData.append("llm_model_name", modelName);

    try {
      const response = await fetch(`${API_BASE_URL}/translate/jobs`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not start translation job.");
      }

      setJob(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsStartingJob(false);
    }
  }

  async function refreshJob(jobId) {
    try {
      const response = await fetch(`${API_BASE_URL}/translate/jobs/${jobId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not refresh job.");
      }

      setJob(data);
    } catch (err) {
      setError(err.message);
    }
  }

  const progress = job && job.total_pages > 0
    ? Math.round((job.completed_pages / job.total_pages) * 100)
    : 0;

  return (
    <main className="app-shell">
      <p className="eyebrow">Yakusu</p>
      <section className="workspace">
        <header className="topbar">
          <div className="header-left">
            <h1>Manga Translator</h1>
            <p className="subtitle">Pro-tip: Try <strong>Groq</strong> with <em>llama-3.3-70b</em> for fast, free high-quality translations.</p>
          </div>
          <div className="header-right">
            <div className="api-pill">{API_BASE_URL}</div>
            <button className="icon-button" onClick={toggleTheme} title="Toggle dark mode">
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>
          </div>
        </header>

        <div className="layout">
          <section className="panel controls-panel">
            <div className="panel-header">
              <Upload size={20} />
              <h2>Upload</h2>
            </div>

            <button className="drop-zone" onClick={() => fileInputRef.current?.click()}>
              <FileImage size={30} />
              <span>Choose manga pages</span>
              <small>Images are sorted by filename before upload.</small>
            </button>
            <input
              ref={fileInputRef}
              className="hidden-input"
              type="file"
              accept="image/*"
              multiple
              onChange={handleFileChange}
            />

            <div className="file-list">
              {sortedFiles.length === 0 ? (
                <p className="muted">No pages selected.</p>
              ) : (
                sortedFiles.map((file, index) => (
                  <div className="file-row" key={`${file.name}-${file.size}-${index}`}>
                    <span>{String(index + 1).padStart(3, "0")}</span>
                    <p>{file.name}</p>
                  </div>
                ))
              )}
            </div>

            <div className="field-grid">
              <label>
                Target language
                <input
                  value={targetLanguage}
                  onChange={(event) => setTargetLanguage(event.target.value)}
                />
              </label>
              <label>
                LLM provider
                <select value={provider} onChange={(event) => setProvider(event.target.value)}>
                  <option value="">Use API settings</option>
                  <option value="gemini">Gemini</option>
                  <option value="openai">OpenAI</option>
                  <option value="claude">Claude</option>
                  <option value="groq">Groq</option>
                  <option value="local">Local</option>
                </select>
              </label>
              <label>
                API key
                <input
                  type="password"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="Optional"
                />
              </label>
              <label>
                Model
                <input
                  value={modelName}
                  onChange={(event) => setModelName(event.target.value)}
                  placeholder="Optional"
                />
              </label>
            </div>

            <div className="button-row">
              <button className="secondary-button" onClick={readFirstPageOcr} disabled={isReadingOcr}>
                {isReadingOcr ? <Loader2 className="spin" size={18} /> : <FileImage size={18} />}
                OCR first page
              </button>
              <button className="primary-button" onClick={startTranslationJob} disabled={isStartingJob}>
                {isStartingJob ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
                Translate chapter
              </button>
            </div>

            {error && (
              <div className="error-line">
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}
          </section>

          <section className="panel output-panel">
            <div className="panel-header">
              <Languages size={20} />
              <h2>Results</h2>
              {job && (
                <button className="icon-button" onClick={() => refreshJob(job.job_id)}>
                  <RefreshCw size={17} />
                </button>
              )}
            </div>

            {job ? (
              <div className="job-status">
                <div className="status-line">
                  <span className={`status-dot ${job.status}`}></span>
                  <strong>{job.status}</strong>
                  <span>{job.completed_pages} / {job.total_pages} pages</span>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                </div>
                {job.error && <p className="error-text">{job.error}</p>}
                {job.result_zip_url && (
                  <a className="download-link" href={job.result_zip_url}>
                    Download chapter ZIP
                  </a>
                )}
              </div>
            ) : (
              <p className="muted">Start OCR or translation to see output.</p>
            )}

            {ocrResult && (
              <div className="ocr-blocks">
                <div className="result-heading">
                  <CheckCircle2 size={18} />
                  <span>{ocrResult.blocks.length} text blocks found</span>
                </div>
                {ocrResult.blocks.map((block) => (
                  <div className="text-block" key={block.id}>
                    <span>{block.id}</span>
                    <p>{block.text}</p>
                  </div>
                ))}
              </div>
            )}

            {job?.pages?.length > 0 && (
              <div className="reader">
                {job.pages.map((page) => (
                  <img key={page.page} src={page.url} alt={`Translated page ${page.page}`} />
                ))}
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

export default App;

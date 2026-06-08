import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, BarChart3, Clapperboard, Eye, Heart, RefreshCw, Users } from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json();
}

function formatNumber(value) {
  return new Intl.NumberFormat("en", { notation: value > 999999 ? "compact" : "standard" }).format(value || 0);
}

function Stat({ icon: Icon, label, value }) {
  return (
    <section className="stat">
      <Icon size={18} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}

function App() {
  const [summary, setSummary] = useState(null);
  const [videos, setVideos] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [audience, setAudience] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [summaryData, videoData, metricData, audienceData] = await Promise.all([
        getJson("/analytics/summary"),
        getJson("/videos/top?limit=8"),
        getJson("/metrics/daily?days=14"),
        getJson("/audience?limit=8"),
      ]);
      setSummary(summaryData);
      setVideos(videoData);
      setMetrics(metricData);
      setAudience(audienceData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const latestByPlatform = useMemo(() => (summary?.platforms || []).slice(0, 3), [summary]);
  const totals = summary?.totals || {};

  return (
    <main>
      <header className="topbar">
        <div>
          <h1>Creator Analytics</h1>
          <p>Unified YouTube, TikTok, and Instagram performance intelligence.</p>
        </div>
        <button className="icon-button" onClick={load} disabled={loading} title="Refresh dashboard">
          <RefreshCw size={18} aria-hidden="true" />
        </button>
      </header>

      {error ? <div className="notice">{error}</div> : null}

      <section className="stats-grid">
        <Stat icon={Clapperboard} label="Videos" value={formatNumber(totals.videos)} />
        <Stat icon={Eye} label="Views" value={formatNumber(totals.views)} />
        <Stat icon={Heart} label="Engagement" value={`${((summary?.engagement_rate || 0) * 100).toFixed(2)}%`} />
        <Stat icon={Activity} label="Watch Time" value={formatNumber(totals.watch_time)} />
      </section>

      <section className="split">
        <div className="panel">
          <div className="panel-title">
            <BarChart3 size={18} aria-hidden="true" />
            <h2>Platform Snapshot</h2>
          </div>
          <div className="platform-list">
            {latestByPlatform.map((item) => (
              <div className="platform-row" key={`${item.platform}-${item.date}`}>
                <span>{item.platform}</span>
                <strong>{formatNumber(item.views)}</strong>
                <meter min="0" max={Math.max(...latestByPlatform.map((p) => p.views), 1)} value={item.views} />
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">
            <Users size={18} aria-hidden="true" />
            <h2>Audience</h2>
          </div>
          <div className="audience-list">
            {audience.map((item) => (
              <div className="audience-row" key={`${item.platform}-${item.region}-${item.age}-${item.gender}`}>
                <span>{item.platform} / {item.region} / {item.age}</span>
                <strong>{formatNumber(item.viewers)}</strong>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">
          <Clapperboard size={18} aria-hidden="true" />
          <h2>Top Content</h2>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Platform</th>
                <th>Title</th>
                <th>Views</th>
                <th>Engagement</th>
                <th>Growth</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((video) => (
                <tr key={video.id}>
                  <td>{video.rank || "-"}</td>
                  <td>{video.platform}</td>
                  <td>{video.title}</td>
                  <td>{formatNumber(video.views)}</td>
                  <td>{((video.engagement_rate || 0) * 100).toFixed(2)}%</td>
                  <td>{video.growth_rate === null ? "-" : `${((video.growth_rate || 0) * 100).toFixed(1)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">
          <Activity size={18} aria-hidden="true" />
          <h2>Daily Metrics</h2>
        </div>
        <div className="metric-strip">
          {metrics.slice(0, 12).map((item) => (
            <div className="metric-chip" key={`${item.date}-${item.platform}`}>
              <span>{item.date}</span>
              <strong>{item.platform}</strong>
              <em>{formatNumber(item.views)} views</em>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);

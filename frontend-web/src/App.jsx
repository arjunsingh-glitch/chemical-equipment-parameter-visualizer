import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register only the Chart.js pieces we actually need for this screen.
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// Small helper so it's easy to point the UI at a different backend later.
const API_BASE_URL = 'http://127.0.0.1:8000/api';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [stats, setStats] = useState(null);
  const [pdfPath, setPdfPath] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // For the task a simple Basic Auth prompt is enough – no JWTs or OAuth here.
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files?.[0] ?? null);
    setError('');
  };

  const fetchHistory = async () => {
    if (!username || !password) return;

    setIsLoadingHistory(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/history/`, {
        auth: {
          username,
          password
        }
      });
      setHistory(response.data);
    } catch (err) {
      // History is a nice extra but not critical, so I just log failures.
      console.error('Failed to fetch history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Whenever the user updates their credentials, refresh the history panel.
  useEffect(() => {
    if (username && password) {
      fetchHistory();
    }
  }, [username, password]);

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a CSV file first.');
      return;
    }
    if (!username || !password) {
      setError('Please enter username and password (Basic Auth).');
      return;
    }

    setIsUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload-equipment/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        auth: {
          username,
          password
        }
      });

      setStats(response.data.stats);
      setPdfPath(response.data.pdf_report);
      // After a successful upload it feels natural to bump the history list.
      fetchHistory();
    } catch (err) {
      // Keep error handling simple and \"human\" – log details and show a short message.
      console.error(err);
      const message = err.response?.data?.error || 'Upload failed. Please check the CSV and your credentials.';
      setError(message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownloadPdf = () => {
    if (!pdfPath) return;
    // The backend returns a relative path like \"media/reports/xyz.pdf\".
    // Opening it in a new tab lets the browser handle preview vs download.
    const url = `http://127.0.0.1:8000/${pdfPath}`;
    window.open(url, '_blank');
  };

  const handleDownloadHistoryPdf = (pdfPath) => {
    const url = `http://127.0.0.1:8000/${pdfPath}`;
    window.open(url, '_blank');
  };

  // Map the backend `type_distribution` object into something Chart.js
  // understands.  Each key (e.g. \"Pump\") becomes a label on the X‑axis.
  const chartData = stats
    ? {
        labels: Object.keys(stats.type_distribution),
        datasets: [
          {
            label: 'Equipment count by type',
            data: Object.values(stats.type_distribution),
            backgroundColor: 'rgba(8, 145, 178, 0.7)', // teal accent
            borderColor: 'rgba(8, 145, 178, 1)',
            borderWidth: 1
          }
        ]
      }
    : null;

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top'
      },
      title: {
        display: true,
        text: 'Equipment Type Distribution'
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-5xl mx-auto p-6">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-primary mb-1">
            Chemical Equipment Parameter Visualizer
          </h1>
          <p className="text-slate-300 text-sm">
            Simple dashboard to upload a CSV file, view summary statistics, and see equipment
            type distribution.
          </p>
        </header>

        <div className="grid md:grid-cols-3 gap-6 mb-8 bg-slate-800 rounded-xl border border-slate-700 p-5">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-slate-200 mb-2">
              Select equipment CSV
            </label>
            <div className="flex items-center gap-3">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="block w-full text-sm text-slate-200 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-accent file:text-slate-900 hover:file:bg-teal-300"
              />
            </div>
            {selectedFile && (
              <p className="mt-2 text-xs text-slate-400">
                Selected: <span className="font-mono">{selectedFile.name}</span>
              </p>
            )}
          </div>

          <div>
            <p className="text-sm font-medium text-slate-200 mb-1">Basic Auth (Django user)</p>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full mb-2 rounded-md bg-slate-900 border border-slate-700 px-3 py-1.5 text-sm"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full mb-3 rounded-md bg-slate-900 border border-slate-700 px-3 py-1.5 text-sm"
            />

            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="w-full inline-flex items-center justify-center rounded-md bg-primary text-sm font-semibold px-3 py-2 text-slate-50 hover:bg-teal-700 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isUploading ? 'Uploading...' : 'Upload CSV'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-red-500 bg-red-900/40 px-4 py-2 text-sm text-red-100">
            {error}
          </div>
        )}

        {stats && (
          <div className="space-y-6">
            <section className="bg-slate-800 border border-slate-700 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-slate-100">Summary statistics</h2>
                <button
                  onClick={handleDownloadPdf}
                  disabled={!pdfPath}
                  className="inline-flex items-center rounded-md border border-accent text-accent px-3 py-1.5 text-xs font-semibold hover:bg-accent hover:text-slate-900 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  Download PDF report
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-300 border-b border-slate-700">
                      <th className="py-2 pr-4">Metric</th>
                      <th className="py-2">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    <tr>
                      <td className="py-2 pr-4 text-slate-200">Total equipment count</td>
                      <td className="py-2 text-slate-100">{stats.total_count}</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-slate-200">Average flowrate</td>
                      <td className="py-2 text-slate-100">
                        {stats.average_flowrate.toFixed(2)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-slate-200">Average pressure</td>
                      <td className="py-2 text-slate-100">
                        {stats.average_pressure.toFixed(2)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-slate-200">Average temperature</td>
                      <td className="py-2 text-slate-100">
                        {stats.average_temperature.toFixed(2)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section className="bg-slate-800 border border-slate-700 rounded-xl p-5">
              <h2 className="text-lg font-semibold text-slate-100 mb-3">
                Equipment type distribution
              </h2>
              {chartData && (
                <div className="bg-slate-900/40 rounded-lg p-4">
                  <Bar data={chartData} options={chartOptions} />
                </div>
              )}
            </section>
          </div>
        )}

        {/* Simple \"recent uploads\" block to match the backend history. */}
        {username && password && (
          <section className="bg-slate-800 border border-slate-700 rounded-xl p-5 mt-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-slate-100">Upload History (Last 5)</h2>
              <button
                onClick={fetchHistory}
                disabled={isLoadingHistory}
                className="inline-flex items-center rounded-md border border-slate-600 text-slate-300 px-3 py-1.5 text-xs font-semibold hover:bg-slate-700 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isLoadingHistory ? 'Loading...' : 'Refresh'}
              </button>
            </div>
            {history.length === 0 ? (
              <p className="text-slate-400 text-sm">No upload history yet.</p>
            ) : (
              <div className="space-y-3">
                {history.map((entry) => (
                  <div
                    key={entry.id}
                    className="bg-slate-900/40 rounded-lg p-4 border border-slate-700"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-slate-200 font-medium text-sm">
                            {entry.original_filename}
                          </span>
                          <span className="text-slate-500 text-xs">
                            {new Date(entry.uploaded_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-slate-300 text-xs">{entry.summary}</p>
                      </div>
                      <button
                        onClick={() => handleDownloadHistoryPdf(entry.pdf_path)}
                        className="ml-4 inline-flex items-center rounded-md border border-accent text-accent px-2 py-1 text-xs font-semibold hover:bg-accent hover:text-slate-900"
                      >
                        PDF
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

export default App;


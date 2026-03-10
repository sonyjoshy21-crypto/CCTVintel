import { useState, useRef, useEffect } from 'react'
import { Upload, Search, ShieldCheck, Zap, Activity, Clock, ShieldAlert, Navigation, FileDown, ArrowLeft, LogIn, Lock, User, LogOut, History, Settings } from 'lucide-react'
import axios from 'axios'
import './index.css'
import { supabase } from './supabaseClient'

function App() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadedFilename, setUploadedFilename] = useState(null)
  
  const [query, setQuery] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [progress, setProgress] = useState({ percent: 0, message: '' })
  
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  
  const fileInputRef = useRef(null)
  const videoRef = useRef(null)
  
  const [videoUrl, setVideoUrl] = useState(null)
  const [annotatedVideoUrl, setAnnotatedVideoUrl] = useState(null)
  const [videoDimensions, setVideoDimensions] = useState({ width: 0, height: 0 })
  const [activeBox, setActiveBox] = useState(null)

  // Auth & View State
  const [view, setView] = useState('home') // 'home', 'results'
  const [session, setSession] = useState(null)
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [authError, setAuthError] = useState(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleSignUp = async (e) => {
    e.preventDefault()
    if (!authEmail || !authPassword) {
      setAuthError("Please enter both an email and password to create an account.")
      return
    }
    setAuthLoading(true)
    setAuthError(null)
    const { error } = await supabase.auth.signUp({
      email: authEmail,
      password: authPassword,
    })
    if (error) setAuthError(error.message)
    else setAuthError('Account created! Check your email for a login link, or try signing in directly.')
    setAuthLoading(false)
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    if (!authEmail || !authPassword) {
      setAuthError("Please enter both an email and password to sign in.")
      return
    }
    setAuthLoading(true)
    setAuthError(null)
    const { error } = await supabase.auth.signInWithPassword({
      email: authEmail,
      password: authPassword,
    })
    if (error) setAuthError(error.message)
    setAuthLoading(false)
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    setView('home')
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      setVideoUrl(URL.createObjectURL(selectedFile))
      setError(null)
      setActiveBox(null)
      // Auto-trigger upload
      handleUpload(selectedFile)
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleUpload = async (selectedFile) => {
    setUploading(true)
    setError(null)
    const formData = new FormData()
    formData.append('video', selectedFile)

    try {
      const response = await axios.post('http://localhost:5000/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setUploadedFilename(response.data.filename)
      setUploading(false)
    } catch (err) {
      console.error(err)
      setError('Failed to upload video. Ensure backend is running.')
      setUploading(false)
    }
  }

  useEffect(() => {
    let intervalId;
    if (analyzing && uploadedFilename) {
      intervalId = setInterval(async () => {
        try {
          const res = await axios.get(`http://localhost:5000/api/progress/${uploadedFilename}`);
          if (res.data && res.data.percent !== undefined) {
            setProgress({ 
              percent: res.data.percent, 
              message: res.data.message || 'Processing video frame by frame...' 
            });
          }
        } catch (err) {
          console.error("Progress polling error", err);
        }
      }, 1000);
    }
    return () => clearInterval(intervalId);
  }, [analyzing, uploadedFilename]);

  const handleAnalyze = async () => {
    if (!uploadedFilename || !query.trim()) return

    setAnalyzing(true)
    setProgress({ percent: 0, message: 'Initializing AI Models...' })
    setError(null)
    setResults(null)
    setActiveBox(null)

    try {
      const response = await axios.post('http://localhost:5000/api/analyze', {
        filename: uploadedFilename,
        query: query
      })
      
      const analysisData = response.data;
      setProgress({ percent: 100, message: 'Complete!' })
      setResults(analysisData)
      setAnalyzing(false)
      // Check if backend returned an annotated video path
      if (analysisData.annotated_video_path) {
        setAnnotatedVideoUrl(`http://localhost:5000/api/video/${analysisData.annotated_video_path}`)
      }
      setView('results')
      
      // Save report to database if logged in
      if (session?.user?.id) {
        saveReportToDatabase(analysisData)
      }
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.error || 'Failed to analyze video.')
      setAnalyzing(false)
      setProgress({ percent: 0, message: '' })
    }
  }

  const saveReportToDatabase = async (data) => {
    try {
      // Aggregate the detections by object name for a cleaner summary
      const objectCounts = {}
      if (data && data.results) {
        data.results.forEach(item => {
          const key = item.object
          if (objectCounts[key]) {
            objectCounts[key] += 1
          } else {
            objectCounts[key] = 1
          }
        })
      }
      
      // Convert counts to string format: "fights: 3 scenes, guy: 2 scenes"
      const aggregatedSummary = Object.entries(objectCounts)
        .map(([obj, count]) => `${obj} : ${count} scenes`)
        .join(' , ') || "No detections"

      const { error } = await supabase
        .from('reports')
        .insert([
          {
            user_id: session.user.id,
            video_name: uploadedFilename,
            query: query,
            results: aggregatedSummary
          }
        ])
      if (error) {
        console.error("Error saving report to Supabase:", error);
      } else {
        console.log("Report saved to database successfully.");
      }
    } catch (err) {
      console.error("Database save exception:", err);
    }
  }

  const handleSeek = (timestamp, bbox, objectName) => {
    if (videoRef.current) {
      videoRef.current.currentTime = timestamp;
      videoRef.current.pause();
      setActiveBox({ bbox, object: objectName });
      videoRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  const exportReport = () => {
    if (!results) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(results, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href",     dataStr);
    downloadAnchorNode.setAttribute("download", `analysis_report_${uploadedFilename}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  }

  // Calculate averages for summary cards
  const getAverageConfidence = () => {
    if (!results || !results.results || results.results.length === 0) return 0;
    const sum = results.results.reduce((acc, curr) => acc + curr.confidence, 0);
    return Math.round((sum / results.results.length) * 100);
  }

  return (
    <>
      <header className="app-header">
        <div className="logo-section cursor-pointer" onClick={() => setView('home')}>
          <div className="logo-icon-bg">
            <Activity size={24} className="logo-icon" />
          </div>
          <div className="logo-text">
            <h1>CCTV Intel ✧</h1>
            <p>AI-Powered Video Analysis</p>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          {session && (
            <button 
              className="nav-btn" 
              title="History"
              onClick={() => setView('history')}
              style={{ color: view === 'history' ? '#9d4edd' : 'inherit' }}
            >
              <History size={20} />
            </button>
          )}
          <button className="nav-btn" title="Settings"><Settings size={20} /></button>
          {session ? (
            <button 
              onClick={handleLogout}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}
            >
              <LogOut size={16} /> Sign Out
            </button>
          ) : null}
          <div className="status-badge">
            <div className="status-dot"></div>
            Online
          </div>
        </div>
      </header>

      <div className="app-container">
        {!session ? (
          <div className="glass-panel" style={{ maxWidth: '400px', marginTop: '4rem' }}>
            <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
              <div className="logo-icon-bg" style={{ width: '64px', height: '64px', margin: '0 auto 1rem auto' }}>
                <Lock size={32} className="logo-icon" />
              </div>
              <h2>Secure Access</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.5rem' }}>Login to access CCTV Intel Analysis</p>
            </div>

            <form onSubmit={handleLogin}>
              <div style={{ marginBottom: '1.5rem' }}>
                <label className="input-label">Email Address</label>
                <div className="search-container" style={{ margin: 0 }}>
                  <User size={18} color="var(--text-muted)" />
                  <input
                    type="email"
                    className="search-input"
                    placeholder="Enter your email"
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div style={{ marginBottom: '2rem' }}>
                <label className="input-label">Password</label>
                <div className="search-container" style={{ margin: 0 }}>
                  <Lock size={18} color="var(--text-muted)" />
                  <input
                    type="password"
                    className="search-input"
                    placeholder="••••••••"
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    required
                  />
                </div>
              </div>

              {authError && (
                <div style={{ padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', borderRadius: '8px', fontSize: '0.85rem', marginBottom: '1.5rem', textAlign: 'center' }}>
                  {authError}
                </div>
              )}

              <button 
                type="submit" 
                className="btn-primary active-btn" 
                disabled={authLoading}
                style={{ marginBottom: '1rem' }}
              >
                {authLoading ? <div className="loader" /> : (
                  <><LogIn size={18} /> Sign In</>
                )}
              </button>

              <button 
                type="button" 
                className="btn-primary" 
                onClick={handleSignUp}
                disabled={authLoading}
                style={{ background: 'transparent', padding: '0.5rem' }}
              >
                Create Account
              </button>
            </form>
          </div>
        ) : view === 'home' && (
          <>
            <section className="hero-section">
              <div className="hero-pill">
                ✧ Next-Gen Object Detection
              </div>
              <h1 className="hero-title">
                Intelligent Video<br /><span>Analysis</span>
              </h1>
              <p className="hero-subtitle">
                Upload your CCTV footage and use AI-powered prompts to detect specific objects, people, or events with precise timestamps
              </p>
              
              <div className="hero-features">
                <div className="feature-item">
                  <Zap size={18} color="#9d4edd" /> Real-time Processing
                </div>
                <div className="feature-item">
                  <ShieldCheck size={18} color="#9d4edd" /> Secure & Private
                </div>
                <div className="feature-item">
                  <Activity size={18} color="#9d4edd" /> AI-Powered
                </div>
              </div>
            </section>

            <div className="glass-panel">
              <div style={{ marginBottom: '1.5rem', fontWeight: 500 }}>Upload Video</div>
              <div 
                className={`upload-zone ${file ? 'active' : ''}`}
                onClick={handleUploadClick}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  accept="video/mp4,video/x-m4v,video/*" 
                  style={{ display: 'none' }} 
                />
                
                <div className="upload-icon-container">
                  <Upload size={32} className="upload-icon" />
                </div>
                
                {uploading ? (
                  <>
                    <div className="upload-title">Uploading to secure server...</div>
                    <div className="loader" style={{margin: '0 auto', marginTop: '1rem'}}></div>
                  </>
                ) : file && uploadedFilename ? (
                  <>
                    <div className="upload-title" style={{color: 'var(--success)'}}>✓ {file.name} Uploaded</div>
                    <div className="upload-subtitle">Ready for analysis</div>
                  </>
                ) : (
                  <>
                    <div className="upload-title">Drop your video here or click to browse</div>
                    <div className="upload-subtitle">Supports MP4, MOV, AVI and more</div>
                  </>
                )}
              </div>

              <div style={{ marginBottom: '1.5rem', fontWeight: 500 }}>Detection Prompt</div>
              <div className="search-container">
                <Search size={20} color="var(--text-muted)" />
                <input 
                  type="text" 
                  className="search-input" 
                  placeholder="e.g., person entering, suspicious package, vehicle..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                />
              </div>
              <span className="text-xs" style={{marginBottom: '1.5rem', display: 'block'}}>Describe what you want to detect in the video</span>

              <button 
                className={`btn-primary ${uploadedFilename && query.trim() && !analyzing ? 'active-btn' : ''}`}
                onClick={handleAnalyze}
                disabled={!uploadedFilename || !query.trim() || analyzing}
              >
                {analyzing ? (
                  <>
                    <div className="loader" /> Analyzing... {progress.percent}%
                  </>
                ) : (
                  <>
                    <Activity size={20} /> Start Analysis
                  </>
                )}
              </button>
              
              {analyzing && (
                <div style={{ marginTop: '1rem', textAlign: 'center', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  {progress.message}
                </div>
              )}
            </div>

            {error && (
              <div style={{ padding: '1.5rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', color: '#f87171', display: 'flex', alignItems: 'center', gap: '1rem', width: '100%', maxWidth: '800px' }}>
                <ShieldAlert size={24} />
                <div>
                  <h3 style={{ marginBottom: '0.25rem' }}>Error Error</h3>
                  <p>{error}</p>
                </div>
              </div>
            )}
          </>
        )}

        {session && view === 'results' && results && (
          <div style={{ width: '100%' }}>
            <div className="results-header-bar">
              <div>
                <button className="back-btn" onClick={() => setView('home')}>
                  <ArrowLeft size={18} /> New Analysis
                </button>
                <h1 style={{ fontSize: '2rem', fontWeight: 500, marginBottom: '0.25rem' }}>Analysis Complete</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  Found {results.matches_found} detections in {uploadedFilename}
                </p>
              </div>
              <button className="btn-primary export-btn" onClick={exportReport}>
                <FileDown size={18} /> Export Report
              </button>
            </div>

            <div className="summary-cards-row">
              <div className="summary-card">
                <div className="summary-card-content">
                  <p>Total Detections</p>
                  <h3>{results.matches_found}</h3>
                </div>
                <div className="summary-icon-wrapper active">
                  <Activity size={24} />
                </div>
              </div>

              <div className="summary-card">
                <div className="summary-card-content">
                  <p>Avg. Confidence</p>
                  <h3>{getAverageConfidence()}%</h3>
                </div>
                <div className="summary-icon-wrapper">
                  <Activity size={24} />
                </div>
              </div>

              <div className="summary-card">
                <div className="summary-card-content">
                  <p>Duration</p>
                  <h3>{results.processing_time_seconds}s</h3>
                </div>
                <div className="summary-icon-wrapper">
                  <Clock size={24} />
                </div>
              </div>
            </div>

            <div className="glass-panel" style={{ maxWidth: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem', fontWeight: 500 }}>
                <Clock size={18} color="var(--primary)" /> Detection Timeline
              </div>
              
              {videoUrl && (
                <div style={{ marginBottom: '2rem' }}>
                  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                    {/* Original Video Player */}
                    <div style={{ flex: '1 1 min(45%, 400px)', display: 'flex', flexDirection: 'column', background: '#000', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <div style={{ padding: '0.5rem', background: 'var(--bg-darker)', textAlign: 'center', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)', borderBottom: '1px solid var(--border-color)' }}>
                        Original Footage
                      </div>
                      <div style={{ position: 'relative', width: '100%', aspectRatio: videoDimensions.width && videoDimensions.height ? `${videoDimensions.width} / ${videoDimensions.height}` : '16/9' }}>
                        <video 
                          ref={videoRef} 
                          src={videoUrl} 
                          controls 
                          onLoadedMetadata={(e) => setVideoDimensions({ width: e.target.videoWidth, height: e.target.videoHeight })}
                          onPlay={() => setActiveBox(null)}
                          style={{ position:'absolute', top:0, left:0, width: '100%', height: '100%', objectFit: 'contain' }} 
                        />
                        {activeBox && videoDimensions.width > 0 && (
                          <div style={{
                            position: 'absolute',
                            border: '3px solid #10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.2)',
                            pointerEvents: 'none',
                            left: `${(activeBox.bbox[0] / videoDimensions.width) * 100}%`,
                            top: `${(activeBox.bbox[1] / videoDimensions.height) * 100}%`,
                            width: `${((activeBox.bbox[2] - activeBox.bbox[0]) / videoDimensions.width) * 100}%`,
                            height: `${((activeBox.bbox[3] - activeBox.bbox[1]) / videoDimensions.height) * 100}%`,
                            boxShadow: '0 0 15px rgba(16, 185, 129, 0.6)',
                            display: 'flex',
                            alignItems: 'flex-start',
                            justifyContent: 'flex-start',
                            zIndex: 10
                          }}>
                            <span style={{ 
                              background: '#10b981', 
                              color: '#000', 
                              fontSize: '12px', 
                              fontWeight: 'bold', 
                              padding: '2px 8px',
                              borderBottomRightRadius: '4px',
                              textTransform: 'uppercase'
                            }}>
                              {activeBox.object}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Annotated Video Player from Backend */}
                    {results.annotated_video_path && (
                      <div style={{ flex: '1 1 min(45%, 400px)', display: 'flex', flexDirection: 'column', background: '#000', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <div style={{ padding: '0.5rem', background: 'var(--bg-darker)', textAlign: 'center', fontSize: '0.85rem', fontWeight: 500, color: '#9d4edd', borderBottom: '1px solid var(--border-color)' }}>
                          <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                            <Zap size={14} /> AI Annotated (YOLO + CLIP)
                          </span>
                        </div>
                        <div style={{ position: 'relative', width: '100%', aspectRatio: '16/9' }}>
                           <video 
                            src={annotatedVideoUrl}
                            controls 
                            style={{ position:'absolute', top:0, left:0, width: '100%', height: '100%', objectFit: 'contain' }} 
                          />
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Interactive Timeline */}
                  {results.results && results.results.length > 0 && videoRef.current && videoRef.current.duration && (
                    <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-darker)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                       <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between' }}>
                          <span>0:00</span>
                          <span>Timeline of Events (Click to seek)</span>
                          <span>{Math.floor(videoRef.current.duration / 60)}:{Math.floor(videoRef.current.duration % 60).toString().padStart(2, '0')}</span>
                       </div>
                       <div style={{ position: 'relative', width: '100%', height: '24px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', cursor: 'pointer', overflow: 'hidden' }}>
                          {results.results.map((res, idx) => {
                             const percentPos = (res.timestamp / videoRef.current.duration) * 100;
                             if (percentPos > 100) return null;
                             return (
                               <div 
                                 key={`tick-${idx}`}
                                 onClick={() => handleSeek(res.timestamp, res.bbox, res.object)}
                                 title={`${res.object} at ${res.timestamp}s`}
                                 style={{
                                    position: 'absolute',
                                    left: `${percentPos}%`,
                                    top: 0,
                                    width: '4px',
                                    height: '100%',
                                    background: '#10b981',
                                    opacity: 0.7,
                                    cursor: 'pointer',
                                    transform: 'translateX(-50%)',
                                    zIndex: 5
                                 }}
                                 onMouseOver={(e) => { e.target.style.opacity = 1; e.target.style.background = '#9d4edd'; }}
                                 onMouseOut={(e) => { e.target.style.opacity = 0.7; e.target.style.background = '#10b981'; }}
                               />
                             )
                          })}
                       </div>
                    </div>
                  )}
                </div>
              )}

              {results.matches_found > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem' }}>
                  {results.results.map((res, idx) => (
                    <div key={idx} style={{ background: 'var(--bg-darker)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <span style={{ fontWeight: 600 }}>{res.object}</span>
                        <span style={{ color: 'var(--primary)', fontSize: '0.85rem' }}>Conf: {(res.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                        {res.color !== "unknown" && <span>Color: {res.color} • </span>}
                        {res.action && res.action !== "unknown" && <span>Action: {res.action} • </span>}
                        Timestamp: {Math.floor(res.timestamp / 60)}:{Math.floor(res.timestamp % 60).toString().padStart(2, '0')}
                      </div>
                      <button 
                        className="btn-primary" 
                        onClick={() => handleSeek(res.timestamp, res.bbox, res.object)}
                        style={{ padding: '0.5rem', fontSize: '0.85rem', background: 'rgba(255,255,255,0.05)' }}
                      >
                        <Navigation size={14} /> Seek Video
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                  <Search size={32} style={{ margin: '0 auto 1rem auto', opacity: 0.5 }} />
                  <p>No matches found matching "{query}"</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  )
}

export default App


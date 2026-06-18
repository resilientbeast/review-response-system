import { useState, useEffect } from 'react';
import Drawer from './Drawer';

const AGENT_STAGES = ['monitor', 'triage', 'research', 'drafter', 'qa', 'escalation'];

const SEED_REVIEWS = [
  {
    id: "seed_01",
    label: "Positive — Glowing 5-star compliment",
    stars: 5,
    badge: "FAST PATH",
    badgeColor: "emerald",
    preview: "Absolutely wonderful evening! The risotto was the best...",
    payload: {
      platform: "google",
      business_id: "loc_demo",
      review: {
        text: "Absolutely wonderful evening! The risotto was the best I have had in London. Staff were incredibly attentive and remembered my partner's dietary requirement without being asked twice. Already booked for next month.",
        rating: 5,
        author: "Emily W.",
        url: "http://demo.platform",
        language: "en",
      },
    },
  },
  {
    id: "seed_02",
    label: "Complaint — Wait time + cold food",
    stars: 2,
    badge: "STANDARD PATH",
    badgeColor: "blue",
    preview: "Waited 45 minutes for our table despite having a reservation...",
    payload: {
      platform: "google",
      business_id: "loc_demo",
      review: {
        text: "Waited 45 minutes for our table despite having a reservation. When the food arrived it was lukewarm. Staff were apologetic but couldn't do much. Won't be returning.",
        rating: 2,
        author: "Marcus R.",
        url: "http://demo.platform",
        language: "en",
      },
    },
  },
  {
    id: "seed_03",
    label: "QA Loop — Triggers revision cycle",
    stars: 1,
    badge: "QA REVISION",
    badgeColor: "amber",
    preview: "Worst experience of my life. The manager was dismissive...",
    payload: {
      platform: "tripadvisor",
      business_id: "loc_demo",
      review: {
        text: "Worst experience of my life. The manager was completely dismissive when I raised my concerns. The food was inedible and no one seemed to care. I will be leaving reviews everywhere I can.",
        rating: 1,
        author: "Sarah K.",
        url: "http://demo.platform",
        language: "en",
      },
    },
  },
  {
    id: "seed_04",
    label: "Escalation — Legal threat",
    stars: 1,
    badge: "ESCALATION",
    badgeColor: "rose",
    preview: "I will be contacting my solicitor regarding the allergic reaction...",
    payload: {
      platform: "google",
      business_id: "loc_demo",
      review: {
        text: "I will be contacting my solicitor regarding the allergic reaction my daughter had after eating here despite us clearly flagging her nut allergy at the time of booking. This is completely unacceptable and potentially dangerous.",
        rating: 1,
        author: "David M.",
        url: "http://demo.platform",
        language: "en",
      },
    },
  },
  {
    id: "seed_05",
    label: "Mixed — Great food, poor service",
    stars: 3,
    badge: "MIXED",
    badgeColor: "violet",
    preview: "The food was genuinely excellent but the service let it down...",
    payload: {
      platform: "yelp",
      business_id: "loc_demo",
      review: {
        text: "The food was genuinely excellent — best steak I have had in years. But the service let it down badly. We waited 20 minutes to be acknowledged after sitting down and had to ask three times for the bill. Would return for the food but the front-of-house needs serious attention.",
        rating: 3,
        author: "James T.",
        url: "http://demo.platform",
        language: "en",
      },
    },
  },
];

export default function App() {
  const [reviews, setReviews] = useState({});
  const [connected, setConnected] = useState(false);
  const [activeReviewId, setActiveReviewId] = useState(null);
  const [drawerHeight, setDrawerHeight] = useState(45);
  const [showModal, setShowModal] = useState(false);
  const [injectStatus, setInjectStatus] = useState("idle");

  useEffect(() => {
    // We connect to the bridge running on port 8001
    const sse = new EventSource('http://localhost:8001/stream');

    sse.onopen = () => setConnected(true);
    sse.onerror = () => setConnected(false);

    sse.addEventListener("message", (e) => {
      try {
        const data = JSON.parse(e.data);
        console.log("Received event:", data);
        
        setReviews(prev => {
          const rev = prev[data.review_id] || {
            id: data.review_id,
            history: [],
            currentAgent: null,
            status: null,
            draftText: "",
            envelope: null
          };

          // Append to history
          const newHistory = [...rev.history, data];
          
          let newAgent = data.agent;
          let newStatus = data.status;

          return {
            ...prev,
            [data.review_id]: {
              ...rev,
              currentAgent: newAgent,
              status: newStatus,
              action: data.trail_entry?.action || data.action || rev.action,
              note: data.trail_entry?.note || data.note || rev.note,
              confidence: data.trail_entry?.confidence || data.confidence || rev.confidence,
              draftText: data.draft_text || rev.draftText,
              qaResult: data.qa_result || rev.qaResult,
              envelope: data.envelope_snapshot || rev.envelope,
              history: newHistory,
              published: data.meta?.published || data.published || rev.published
            }
          };
        });
      } catch (err) {
        console.error("Parse error:", err);
      }
    });

    return () => {
      sse.close();
    };
  }, []);

  const injectMock = async (payload) => {
    setShowModal(false);
    setInjectStatus("loading");

    try {
      // dynamically set timestamp
      payload.review.timestamp = new Date().toISOString();
      
      const res = await fetch('http://localhost:8002/inject', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        console.warn("Local injection failed, trying webhook receiver fallback...");
        const fallbackRes = await fetch('http://localhost:8000/demo/inject', { 
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!fallbackRes.ok) throw new Error(`${fallbackRes.status}`);
      }
      
      setInjectStatus("success");
      setTimeout(() => setInjectStatus("idle"), 2000);
    } catch (e) {
      console.error("Failed to inject", e);
      setInjectStatus("error");
      setTimeout(() => setInjectStatus("idle"), 3000);
    }
  };

  const toggleReview = (id) => {
    setActiveReviewId(prev => prev === id ? null : id);
  };

  const getReviewsInStage = (stage) => {
    return Object.values(reviews).filter(r => {
      if (r.published || r.currentAgent === 'system') {
        return stage === 'escalation';
      }
      return r.currentAgent === stage;
    });
  };

  return (
    <div className="min-h-screen p-4 flex flex-col">
      <header className="flex justify-between items-center mb-6 bg-surface p-4 rounded-lg border border-border">
        <div>
          <h1 className="text-xl font-bold text-textPrimary tracking-wide">Review Response <span className="text-blue">Pipeline</span></h1>
          <div className="flex items-center text-sm mt-1">
            <span className={`w-2 h-2 rounded-full mr-2 ${connected ? 'bg-emerald' : 'bg-rose'}`}></span>
            <span className="text-textSub">{connected ? 'Live' : 'Disconnected'}</span>
          </div>
        </div>
        <button 
          onClick={() => setShowModal(true)}
          className={`font-semibold py-2 px-4 rounded transition-colors ${
            injectStatus === 'success' ? 'bg-emerald text-bg' :
            injectStatus === 'error' ? 'bg-rose text-bg' :
            'bg-blue hover:bg-blue/80 text-bg'
          }`}
        >
          {injectStatus === 'success' ? '✓ Injected' :
           injectStatus === 'error' ? '⚠ Offline' :
           'Inject Review'}
        </button>
      </header>

      <div 
        className="flex-1 flex gap-4 overflow-x-auto pb-4 transition-all duration-300"
        style={{ paddingBottom: activeReviewId ? `calc(${drawerHeight}vh + 1rem)` : '1rem' }}
      >
        {AGENT_STAGES.map(stage => (
          <div key={stage} className="flex-1 min-w-[300px] bg-surface rounded-lg border border-border flex flex-col">
            <div className="p-3 border-b border-border bg-bg/50">
              <h2 className="text-sm font-bold uppercase tracking-wider text-textPrimary">{stage}</h2>
              <div className="text-xs text-textSub mt-1">{getReviewsInStage(stage).length} active</div>
            </div>
            
            <div className="p-3 flex-1 overflow-y-auto space-y-3">
              {getReviewsInStage(stage).map(rev => (
                <ReviewCard 
                  key={rev.id} 
                  review={rev} 
                  isActive={rev.id === activeReviewId}
                  onClick={() => toggleReview(rev.id)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <Drawer 
        review={activeReviewId ? reviews[activeReviewId] : null}
        onClose={() => setActiveReviewId(null)}
        drawerHeight={drawerHeight}
        setDrawerHeight={setDrawerHeight}
      />

      {showModal && (
        <InjectModal 
          onClose={() => setShowModal(false)} 
          onInject={injectMock} 
        />
      )}
    </div>
  );
}

function ReviewCard({ review, isActive, onClick }) {
  const isError = review.status === 'error';
  const isDone = review.status === 'done';
  const isWaiting = review.status === 'waiting';
  
  let statusColor = 'border-border bg-surface';
  let pill = '';
  let pillColor = '';
  
  if (isActive) {
    statusColor = 'border-amber bg-amberFaint border-2';
    pill = 'active';
    pillColor = 'text-amber';
  } else if (isError) {
    statusColor = 'border-rose bg-roseFaint border';
    pill = 'failed';
    pillColor = 'text-rose';
  } else if (isDone || review.published) {
    statusColor = 'border-emerald bg-emeraldFaint border';
    pill = review.published ? 'published' : 'done';
    pillColor = 'text-emerald';
  }

  const customerName = review.envelope?.review?.author || 'Customer';
  const rating = review.envelope?.review?.rating || 0;
  const platform = (review.envelope?.platform || "GOOGLE").toUpperCase();
  const text = review.envelope?.review?.text || "";
  const timeStr = review.history && review.history.length > 0 && review.history[0].timestamp 
    ? new Date(review.history[0].timestamp).toLocaleTimeString([], {hour12:false, hour:'2-digit', minute:'2-digit'})
    : '';

  return (
    <div 
      className={`p-3 rounded flex flex-col gap-2 ${statusColor} transition-all cursor-pointer hover:border-amber/50`}
      onClick={onClick}
    >
      <div className="flex justify-between items-start text-[10px]">
        <div className="font-bold text-violet">{platform}</div>
        <div className="text-amber font-mono">
          {'★'.repeat(rating)}{'☆'.repeat(5-rating)}
        </div>
      </div>
      
      <div className="font-bold text-textPrimary text-sm truncate">
        {customerName}
      </div>
      
      <div className="text-xs text-textPrimary italic line-clamp-1 opacity-80">
        "{text}"
      </div>
      
      <div className="flex justify-between items-center mt-1 text-[10px] font-mono text-textMuted uppercase tracking-wider">
        <div>{timeStr}</div>
        {pill && <div className={`${pillColor}`}>{pill}</div>}
      </div>

    </div>
  );
}

function InjectModal({ onClose, onInject }) {
  const [selectedId, setSelectedId] = useState("seed_02");

  // Close on Escape key
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const selectedScenario = SEED_REVIEWS.find(s => s.id === selectedId);

  return (
    <div 
      className="fixed inset-0 bg-bg/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div 
        className="bg-surface border border-border rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-4 border-b border-border flex justify-between items-center bg-bg/50 rounded-t-lg">
          <h2 className="text-lg font-bold text-textPrimary tracking-wide">Select Review Scenario</h2>
          <button onClick={onClose} className="text-textSub hover:text-rose transition-colors text-xl font-bold">✕</button>
        </div>
        
        <div className="p-4 overflow-y-auto space-y-2 flex-1">
          {SEED_REVIEWS.map((scenario) => {
            const isSelected = selectedId === scenario.id;
            
            const badgeColors = {
              emerald: 'bg-emerald text-bg',
              blue: 'bg-blue text-bg',
              amber: 'bg-amber text-bg',
              rose: 'bg-rose text-bg',
              violet: 'bg-violet text-bg',
            };
            const badgeClass = badgeColors[scenario.badgeColor] || badgeColors.blue;
            
            return (
              <div 
                key={scenario.id} 
                onClick={() => setSelectedId(scenario.id)}
                className={`p-3 rounded-lg border transition-all cursor-pointer flex gap-3 items-start ${
                  isSelected 
                    ? 'border-amber bg-amberFaint' 
                    : 'border-border bg-surface hover:border-amber/50'
                }`}
              >
                <div className="mt-1 flex-shrink-0">
                  <div className={`w-3 h-3 rounded-full border ${
                    isSelected ? 'bg-amber border-amber' : 'border-textSub/50 bg-transparent'
                  }`} />
                </div>
                
                <div className="flex-1 flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="text-amber text-sm font-mono tracking-tighter">
                      {'★'.repeat(scenario.stars)}{'☆'.repeat(5 - scenario.stars)}
                    </span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${badgeClass}`}>
                      {scenario.badge}
                    </span>
                  </div>
                  
                  <div className="text-[13px] font-bold text-textPrimary">
                    {scenario.label}
                  </div>
                  
                  <div className="text-[11px] text-textSub italic line-clamp-1">
                    "{scenario.preview}"
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="p-4 border-t border-border bg-bg/50 rounded-b-lg flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 text-sm font-semibold text-textSub hover:text-textPrimary transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={() => onInject(selectedScenario?.payload)}
            disabled={!selectedId}
            className="px-4 py-2 text-sm font-semibold bg-amber hover:bg-amber/80 text-bg disabled:bg-border disabled:text-textSub rounded transition-colors"
          >
            Inject Selected →
          </button>
        </div>
      </div>
    </div>
  );
}

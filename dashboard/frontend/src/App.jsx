import { useState, useEffect } from 'react';
import Drawer from './Drawer';

const AGENT_STAGES = ['monitor', 'triage', 'research', 'drafter', 'qa', 'escalation', 'system'];

export default function App() {
  const [reviews, setReviews] = useState({});
  const [connected, setConnected] = useState(false);
  const [activeReviewId, setActiveReviewId] = useState(null);
  const [drawerHeight, setDrawerHeight] = useState(45);

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
          
          // Determine current agent
          // For system publish, we might just set it to system
          let newAgent = data.agent;
          let newStatus = data.status;
          
          // If a done event has an edge, we could visually move it to the edge destination as 'waiting' 
          // or just leave it in current agent as 'done' until the next agent picks it up.
          // Leaving it in current agent as 'done' is better.

          return {
            ...prev,
            [data.review_id]: {
              ...rev,
              currentAgent: newAgent,
              status: newStatus,
              action: data.action || rev.action,
              note: data.note || rev.note,
              confidence: data.confidence || rev.confidence,
              draftText: data.draft_text || rev.draftText,
              qaResult: data.qa_result || rev.qaResult,
              envelope: data.envelope || rev.envelope,
              history: newHistory,
              published: data.published || rev.published
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

  const injectMock = async () => {
    try {
      const mockData = {
        reviewer_name: "Marcus R.",
        rating: 2,
        text: "Waited 45 minutes for our table despite having a reservation. When the food arrived it was lukewarm. Staff were apologetic but couldn't do much. Won't be returning."
      };
      
      const res = await fetch('http://localhost:8002/inject', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mockData)
      });
      
      if (!res.ok) {
        console.warn("Local injection failed, trying webhook receiver fallback...");
        await fetch('http://localhost:8000/demo/inject', { 
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mockData)
        });
      }
    } catch (e) {
      console.error("Failed to inject", e);
    }
  };

  const toggleReview = (id) => {
    setActiveReviewId(prev => prev === id ? null : id);
  };

  const getReviewsInStage = (stage) => {
    return Object.values(reviews).filter(r => {
      if (stage === 'system' && r.published) return true;
      if (r.published) return false;
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
          onClick={injectMock}
          className="bg-blue hover:bg-blue/80 text-bg font-semibold py-2 px-4 rounded transition-colors"
        >
          Inject Review
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

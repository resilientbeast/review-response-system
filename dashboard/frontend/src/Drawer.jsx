import React, { useState, useEffect, useRef } from 'react';

const QA_CHECKS = [
  { key: "within_character_limit",       label: "Within character limit",        hardFail: true  },
  { key: "addresses_core_complaint",     label: "Addresses core complaint",       hardFail: true  },
  { key: "empathetic_opening",           label: "Empathetic opening",             hardFail: false },
  { key: "no_legal_liability_admission", label: "No legal liability admission",   hardFail: true  },
  { key: "no_public_compensation_offer", label: "No public compensation offer",   hardFail: true  },
  { key: "no_defensive_language",        label: "No defensive language",          hardFail: false },
  { key: "has_action_step",              label: "Has action step",                hardFail: false },
  { key: "appropriate_tone",             label: "Appropriate tone",               hardFail: false },
  { key: "brand_voice_consistent",       label: "Brand voice consistent",         hardFail: false },
  { key: "not_generic",                  label: "Not generic",                    hardFail: false },
];

export default function Drawer({ review, onClose, drawerHeight, setDrawerHeight }) {
  const dragRef = useRef(null);
  
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!dragRef.current) return;
      const newHeight = ((window.innerHeight - e.clientY) / window.innerHeight) * 100;
      if (newHeight >= 30 && newHeight <= 65) {
        setDrawerHeight(newHeight);
      }
    };
    
    const handleMouseUp = () => {
      dragRef.current = false;
      document.body.style.cursor = 'default';
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [setDrawerHeight]);

  const handleMouseDown = () => {
    dragRef.current = true;
    document.body.style.cursor = 'ns-resize';
  };

  const customerName = review?.envelope?.review?.author || 'Customer';
  const rating = review?.envelope?.review?.rating || 0;
  const platform = (review?.envelope?.platform || "GOOGLE").toUpperCase();
  const reviewText = review?.envelope?.review?.text || "";
  const reviewId = review?.id || "";
  const truncatedText = reviewText.length > 60 ? reviewText.substring(0, 60) + "..." : reviewText;

  const transformStyle = review ? 'translateY(0)' : 'translateY(100%)';
  const transitionStyle = review ? 'transform 300ms ease-out' : 'transform 200ms ease-in';

  return (
    <div 
      className="fixed bottom-0 left-0 right-0 bg-surface border-t border-border flex flex-col z-50 shadow-2xl"
      style={{ height: `${drawerHeight}vh`, transform: transformStyle, transition: transitionStyle }}
    >
      <div 
        className="absolute top-0 left-0 right-0 h-1 hover:bg-borderBright cursor-ns-resize z-10"
        onMouseDown={handleMouseDown}
        onDoubleClick={() => setDrawerHeight(45)}
      />
      
      <div className="flex justify-between items-center px-4 py-2 border-b border-border bg-bg/50">
        <div className="flex items-center gap-4 text-sm">
          <span className="font-bold text-violet bg-violet/10 px-2 py-0.5 rounded">{platform}</span>
          <span className="text-amber font-mono">{'★'.repeat(rating)}{'☆'.repeat(5-rating)}</span>
          <span className="font-bold text-textPrimary">{customerName}</span>
          <span className="text-textSub italic">"{truncatedText}"</span>
          <span className="text-textMuted font-mono ml-4">{reviewId}</span>
        </div>
        <button onClick={onClose} className="text-textSub hover:text-textPrimary transition-colors px-2">✕</button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/4 border-r border-border flex flex-col">
          <ContextEnvelopePanel envelope={review?.envelope} />
        </div>
        <div className="w-[22%] border-r border-border flex flex-col">
          <ReasoningTrailPanel history={review?.history} status={review?.status} />
        </div>
        {review?.envelope?.escalation?.required || review?.envelope?.triage?.escalate_flag || review?.status === 'waiting' || review?.status === 'escalated' ? (
          <div className="flex-1 flex flex-col">
            <EscalationPanel envelope={review?.envelope} reviewId={review?.id} />
          </div>
        ) : (
          <>
            <div className="w-1/4 border-r border-border flex flex-col">
              <QAPanel qa={review?.envelope?.qa} isPublished={review?.published} />
            </div>
            <div className="flex-1 flex flex-col">
              <DraftPanel draft={review?.envelope?.draft} isPublished={review?.published} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ContextEnvelopePanel({ envelope }) {
  const sections = ['review', 'triage', 'research', 'draft', 'qa'];
  
  if (!envelope) {
    return <div className="flex-1 p-4 text-textMuted font-mono text-xs flex items-center justify-center">// awaiting first handoff...</div>;
  }

  // Find the latest section that has data
  let latestSection = '';
  for (let i = sections.length - 1; i >= 0; i--) {
    const key = sections[i];
    if (envelope[key] && Object.keys(envelope[key]).length > 0) {
      latestSection = key;
      break;
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-bg font-mono text-[10px] space-y-2">
      <div className="text-xs font-bold text-textPrimary mb-3 uppercase tracking-wider sticky top-0 bg-bg pb-2 border-b border-border z-10">Context Envelope</div>
      {sections.map(section => {
        const data = envelope[section];
        if (!data || Object.keys(data).length === 0) return null;
        const isLatest = section === latestSection;
        
        return (
          <EnvelopeSection key={section} title={section} data={data} isLatest={isLatest} />
        );
      })}
    </div>
  );
}

function EnvelopeSection({ title, data, isLatest }) {
  const [expanded, setExpanded] = useState(isLatest);
  
  useEffect(() => {
    setExpanded(isLatest);
  }, [isLatest]);

  const renderValue = (val) => {
    if (typeof val === 'string') return <span className="text-[#98C870]">"{val}"</span>;
    if (typeof val === 'number') return <span className="text-[#06B6D4]">{val}</span>;
    if (typeof val === 'boolean') return <span className="text-[#8B5CF6]">{val ? 'true' : 'false'}</span>;
    if (val === null) return <span className="text-textMuted">null</span>;
    if (Array.isArray(val) || typeof val === 'object') {
      return <span className="text-textSub">{Array.isArray(val) ? '[...]' : '{...}'}</span>;
    }
    return String(val);
  };

  return (
    <div className={`rounded border ${isLatest ? 'border-l-2 border-l-amber border-border bg-surface' : 'border-border bg-bg/50'} overflow-hidden transition-all`}>
      <div 
        className="px-2 py-1.5 flex justify-between items-center cursor-pointer hover:bg-borderBright/30"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-[#6B9AD0] font-bold">"{title}"</span>: 
          {isLatest && <span className="text-[8px] bg-amber/20 text-amber px-1 rounded ml-2">NEW</span>}
        </div>
        <span className="text-textMuted text-[10px]">{expanded ? '▼' : '▶'}</span>
      </div>
      {expanded && (
        <div className="p-2 border-t border-border/50 pl-4 space-y-1 overflow-x-auto">
          {Object.entries(data).map(([k, v]) => (
            <div key={k} className="flex gap-2">
              <span className="text-[#6B9AD0] whitespace-nowrap">"{k}"</span>: <span className="break-all">{renderValue(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReasoningTrailPanel({ history, status }) {
  const bottomRef = useRef(null);
  
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [history]);

  if (!history || history.length === 0) {
    return <div className="flex-1 p-4 text-textMuted font-mono text-xs flex items-center justify-center">// pipeline not yet started</div>;
  }

  const getAgentColor = (agent) => {
    switch(agent) {
      case 'monitor': return 'text-[#3B82F6]';
      case 'triage': return 'text-[#8B5CF6]';
      case 'research': return 'text-[#F59E0B]';
      case 'drafter': return 'text-[#06B6D4]';
      case 'qa': return 'text-[#10B981]';
      case 'escalation': return 'text-[#F43F5E]';
      default: return 'text-textPrimary';
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-surface flex flex-col">
      <div className="text-xs font-bold text-textPrimary mb-4 uppercase tracking-wider sticky top-0 bg-surface pb-2 border-b border-border z-10">Reasoning Trail</div>
      <div className="flex-1 space-y-4">
        {history.map((event, i) => {
          const isProcessing = event.status === 'processing';
          const isError = event.status === 'error';
          const isDone = event.status === 'done';
          
          let dotColor = 'bg-amber';
          let dotClass = '';
          if (isError) dotColor = 'bg-rose';
          else if (isDone || event.status === 'published') dotColor = 'bg-emerald';
          else if (isProcessing) {
            dotColor = 'bg-amber';
            dotClass = 'animate-pulse';
          }

          const timeStr = event.timestamp ? new Date(event.timestamp).toLocaleTimeString([], {hour12:false, hour:'2-digit', minute:'2-digit', second:'2-digit'}) : '';

          return (
            <div key={i} className="flex gap-3 text-[9px] font-mono">
              <div className="mt-1.5 flex flex-col items-center">
                <div className={`w-2 h-2 rounded-full ${dotColor} ${dotClass}`} />
                {i < history.length - 1 && <div className="w-[1px] h-full bg-border mt-1"></div>}
              </div>
              <div className="flex-1 pb-2">
                <div className="flex justify-between items-start mb-0.5">
                  <span className={`font-bold ${getAgentColor(event.agent)} uppercase`}>{event.agent}</span>
                  <span className="text-textMuted">{timeStr}</span>
                </div>
                <div className="text-textPrimary leading-tight mb-0.5">{event.trail_entry?.action || event.action}</div>
                {(event.trail_entry?.note || event.note) && <div className="text-textSub text-[8px] leading-tight">{event.trail_entry?.note || event.note}</div>}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function QAPanel({ qa, isPublished }) {
  if (!qa || Object.keys(qa).length === 0 || !qa.checks || Object.keys(qa.checks).length === 0) {
    return <div className="flex-1 p-4 text-textMuted font-mono text-xs flex items-center justify-center">// awaiting QA agent</div>;
  }

  const rawScore = qa.qa_score ?? qa.overall_score ?? 0;
  const score = rawScore <= 1 ? Math.round(rawScore * 100) : rawScore;
  const verdict = qa.qa_verdict ?? (qa.passed ? 'approved' : 'rejected');
  
  let scoreColor = 'bg-rose';
  if (score >= 80) scoreColor = 'bg-emerald';
  else if (score >= 60) scoreColor = 'bg-amber';

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-bg flex flex-col font-mono text-[10px]">
      <div className="flex justify-between items-center mb-4 sticky top-0 bg-bg pb-2 border-b border-border z-10">
        <div className="text-xs font-bold text-textPrimary uppercase tracking-wider">QA Checks</div>
        <div className="flex gap-2">
          {(qa.revision_count > 0 || qa.revision > 0) && (
            <span className="text-amber bg-amber/10 px-1.5 py-0.5 rounded border border-amber/20">
              {qa.revision_count || qa.revision} revision{qa.revision_count !== 1 ? 's' : ''} ↺
            </span>
          )}
          {verdict === 'approved' && <span className="text-emerald font-bold">APPROVED ✓</span>}
          {verdict === 'rejected' && <span className="text-rose font-bold">FAILED ✗</span>}
        </div>
      </div>

      <div className="mb-4">
        <div className="flex justify-between text-[9px] mb-1 text-textSub">
          <span>QA SCORE</span>
          <span>{score} / 100</span>
        </div>
        <div className="h-2 bg-surface rounded overflow-hidden border border-border">
          <div className={`h-full ${scoreColor} transition-all duration-500`} style={{ width: `${score}%` }} />
        </div>
      </div>

      <div className="space-y-1.5 flex-1">
        {QA_CHECKS.map(check => {
          const passed = qa.checks[check.key] === true;
          const isHardFail = check.hardFail && !passed;
          const isSoftFail = !check.hardFail && !passed;
          
          let rowClass = 'bg-emeraldFaint border-emerald/25 text-emerald';
          if (isHardFail) rowClass = 'bg-roseFaint border-rose/25 text-rose border-l-2 border-l-amber';
          else if (isSoftFail) rowClass = 'bg-roseFaint border-rose/25 text-rose';

          return (
            <div key={check.key} className={`px-2 py-1.5 rounded border flex items-center gap-2 ${rowClass}`}>
              <span className="w-3 text-center">{passed ? '✓' : '✗'}</span>
              {isHardFail && <span className="text-amber">⚠</span>}
              <span className="flex-1 truncate">{check.label}</span>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-3 border-t border-border text-center">
        {verdict === 'rejected' && (
          <div className="text-rose font-bold mb-1">→ Routing back to Drafter
            <div className="text-[8px] font-normal opacity-80 mt-1">
              {QA_CHECKS.filter(c => qa.checks[c.key] === false).map(c => c.label).join(' • ')}
            </div>
          </div>
        )}
        {verdict === 'approved' && <div className="text-emerald font-bold">✓ Approved — routing to Escalation</div>}
      </div>
    </div>
  );
}

function DraftPanel({ draft, isPublished }) {
  if (!draft || (!draft.response_text && !draft.text)) {
    return <div className="flex-1 p-4 text-textMuted font-mono text-xs flex items-center justify-center">// awaiting Drafter...</div>;
  }

  const text = draft.response_text || draft.text || "";
  const version = draft.version || 1;
  const wordCount = draft.word_count || text.split(/\s+/).length;
  const charCount = draft.char_count || text.length;

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-surface flex flex-col">
      <div className="flex justify-between items-center mb-4 sticky top-0 bg-surface pb-2 border-b border-border z-10">
        <div className="text-xs font-bold text-textPrimary uppercase tracking-wider">
          {isPublished ? 'PUBLISHED RESPONSE' : 'DRAFT RESPONSE'}
        </div>
        {!isPublished && (
          <span className="text-[10px] font-mono text-blue bg-blue/10 px-1.5 py-0.5 rounded border border-blue/20">
            v{version}
          </span>
        )}
      </div>

      {isPublished && (
        <div className="mb-4 bg-emeraldFaint border border-emerald/35 text-emerald font-mono text-[8px] font-bold p-2 rounded flex items-center justify-center gap-2">
          ✓ LIVE ON GOOGLE BUSINESS PROFILE
        </div>
      )}

      <div 
        key={text} 
        className={`flex-1 overflow-y-auto text-sm leading-relaxed animate-[fadeIn_0.3s_ease-out] ${isPublished ? 'text-textPrimary font-normal' : 'text-[#7A9AB8] italic'}`}
      >
        {!isPublished && '"'}{text}{!isPublished && '"'}
      </div>

      <div className="mt-4 pt-2 border-t border-border text-[8px] font-mono text-textMuted text-right">
        {wordCount} words · {charCount} chars
      </div>
    </div>
  );
}

function EscalationPanel({ envelope, reviewId }) {
  if (!envelope) return null;
  const reason = envelope.escalation?.reason || "Critical rating/keywords or confidence threshold.";
  const status = envelope.escalation?.status || "pending";
  const r = envelope.review || {};
  const t = envelope.triage || {};

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-surface flex flex-col">
      <div className="flex justify-between items-center mb-4 sticky top-0 bg-surface pb-2 border-b border-border z-10">
        <div className="text-xs font-bold text-textPrimary uppercase tracking-wider text-rose">
          ESCALATION REQUIRED
        </div>
        <span className="text-[10px] font-mono text-rose bg-rose/10 px-1.5 py-0.5 rounded border border-rose/20">
          {status.toUpperCase()}
        </span>
      </div>

      <div className="mb-4 bg-roseFaint border border-rose/35 text-rose font-mono text-[10px] p-3 rounded">
        <strong>🚨 ESCALATION BRIEF — {reviewId || envelope.review_id}</strong><br/><br/>
        Platform: {String(envelope.platform || '').toUpperCase()} | Rating: {r.rating}/5<br/>
        Urgency: {String(t.urgency || '').toUpperCase()} | Sentiment: {String(t.sentiment || '').toUpperCase()}<br/>
        Reason for escalation: {reason}<br/>
      </div>

      <div className="text-sm leading-relaxed text-textPrimary mb-4">
        <strong>Triage reasoning:</strong><br/>
        {t.reasoning || 'N/A'}
      </div>

      <div className="text-xs font-mono text-textMuted bg-bg/50 p-2 rounded border border-border">
        // Sent to Slack / Band.ai<br/>
        To approve: @escalation approve {reviewId || envelope.review_id}<br/>
        To reject: @escalation redraft {reviewId || envelope.review_id} [your notes]
      </div>
    </div>
  );
}



import { Link } from 'react-router-dom';

interface DecisionCardProps {
  rfp: {
    id: number;
    rfp_id: string;
    title: string;
    agency: string;
    decision_recommendation?: string;
    confidence_level?: number;
    overall_score?: number;
    triage_score?: number;
    response_deadline?: string;
  };
  onApprove: (rfpId: string) => void;
  onReject: (rfpId: string) => void;
  onAnalyze?: (rfpId: string) => void;
  isAnalyzing?: boolean;
}

export default function DecisionCard({ rfp, onApprove, onReject, onAnalyze, isAnalyzing }: DecisionCardProps) {
  const getRecommendationColor = (rec?: string) => {
    switch (rec) {
      case 'go':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'no-go':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <Link
            to={`/rfps/${rfp.rfp_id}`}
            className="text-lg font-semibold hover:text-blue-600 dark:hover:text-blue-400"
          >
            {rfp.title}
          </Link>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{rfp.agency}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRecommendationColor(rfp.decision_recommendation)}`}>
          {rfp.decision_recommendation || 'Pending'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Overall Score</p>
          <p className="text-2xl font-bold">{rfp.overall_score?.toFixed(1) || 'N/A'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Confidence</p>
          <p className="text-2xl font-bold">
            {rfp.confidence_level ? `${(rfp.confidence_level * 100).toFixed(0)}%` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Show analyze button if no scores */}
      {rfp.overall_score == null && onAnalyze && (
        <button
          onClick={() => onAnalyze(rfp.rfp_id)}
          disabled={isAnalyzing}
          className="w-full mb-3 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isAnalyzing ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </>
          ) : (
            'Run Analysis'
          )}
        </button>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => onApprove(rfp.rfp_id)}
          disabled={rfp.overall_score == null}
          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Approve
        </button>
        <button
          onClick={() => onReject(rfp.rfp_id)}
          disabled={rfp.overall_score == null}
          className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Reject
        </button>
      </div>
    </div>
  );
}

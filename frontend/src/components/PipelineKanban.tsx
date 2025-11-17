import React from 'react';
import { Link } from 'react-router-dom';

interface RFP {
  id: number;
  rfp_id: string;
  title: string;
  agency: string;
  current_stage: string;
  triage_score?: number;
}

interface PipelineKanbanProps {
  rfps: RFP[];
}

const stages = [
  { key: 'discovered', label: 'Discovered', color: 'blue' },
  { key: 'triaged', label: 'Triaged', color: 'purple' },
  { key: 'analyzing', label: 'Analyzing', color: 'yellow' },
  { key: 'pricing', label: 'Pricing', color: 'orange' },
  { key: 'approved', label: 'Approved', color: 'green' },
  { key: 'submitted', label: 'Submitted', color: 'teal' },
];

export default function PipelineKanban({ rfps }: PipelineKanbanProps) {
  const getRFPsByStage = (stage: string) => {
    return rfps.filter((rfp) => rfp.current_stage === stage);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {stages.map((stage) => {
        const stageRFPs = getRFPsByStage(stage.key);
        return (
          <div key={stage.key} className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold text-sm">{stage.label}</h3>
              <span className={`px-2 py-1 rounded-full text-xs bg-${stage.color}-100 text-${stage.color}-800 dark:bg-${stage.color}-900 dark:text-${stage.color}-200`}>
                {stageRFPs.length}
              </span>
            </div>
            <div className="space-y-2">
              {stageRFPs.map((rfp) => (
                <Link
                  key={rfp.id}
                  to={`/rfps/${rfp.rfp_id}`}
                  className="block bg-white dark:bg-gray-800 rounded p-3 shadow-sm hover:shadow-md transition"
                >
                  <h4 className="font-medium text-sm line-clamp-2">{rfp.title}</h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{rfp.agency}</p>
                  {rfp.triage_score && (
                    <p className="text-xs font-semibold mt-2">
                      Score: {rfp.triage_score.toFixed(1)}
                    </p>
                  )}
                </Link>
              ))}
              {stageRFPs.length === 0 && (
                <p className="text-xs text-gray-400 text-center py-4">No RFPs</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

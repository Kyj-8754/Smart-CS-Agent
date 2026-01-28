import { colors } from '../styles/colors';
import './ApprovalDialog.css';

const ApprovalDialog = ({ approval, onApprove, onReject }) => {
  const renderDataField = (key, value) => {
    if (typeof value === 'object' && value !== null) {
      return (
        <div className="data-nested">
          <strong>{key}:</strong>
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="data-item">
              <span className="data-key">{k}</span>
              <span className="data-value">{String(v)}</span>
            </div>
          ))}
        </div>
      );
    }
    return (
      <div className="data-item">
        <span className="data-key">{key}</span>
        <span className="data-value">{String(value)}</span>
      </div>
    );
  };

  return (
    <div className="approval-overlay">
      <div className="approval-dialog">
        <div className="approval-header" style={{ backgroundColor: colors.primary }}>
          <h3>승인 요청</h3>
        </div>
        
        <div className="approval-content">
          <p className="approval-description">{approval.description}</p>
          
          {approval.data && (
            <div className="approval-data">
              <h4>세부 정보</h4>
              <div className="data-grid">
                {Object.entries(approval.data).map(([key, value]) => (
                  <div key={key}>
                    {renderDataField(key, value)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className="approval-actions">
          <button
            onClick={onReject}
            className="reject-button"
          >
            취소
          </button>
          <button
            onClick={onApprove}
            className="approve-button"
            style={{ backgroundColor: colors.accent }}
          >
            승인
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApprovalDialog;

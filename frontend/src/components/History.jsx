import React, { useState, useEffect } from 'react';
import { getHistory, sendFeedback } from '../services/api';
import { getCurrentUser } from '../services/auth';
import './History.css';

const History = () => {
    const [historyItems, setHistoryItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 15;

    // Pagination Logic
    const indexOfLastItem = currentPage * ITEMS_PER_PAGE;
    const indexOfFirstItem = indexOfLastItem - ITEMS_PER_PAGE;
    const currentItems = historyItems.slice(indexOfFirstItem, indexOfLastItem);
    const totalPages = Math.ceil(historyItems.length / ITEMS_PER_PAGE);

    useEffect(() => {
        const fetchHistory = async () => {
            const user = getCurrentUser();
            if (user) {
                try {
                    const data = await getHistory(user.id);
                    setHistoryItems(data);
                } catch (error) {
                    console.error("Failed to load history", error);
                } finally {
                    setLoading(false);
                }
            } else {
                setLoading(false);
            }
        };

        fetchHistory();
    }, []);

    const handleFeedback = async (id, type) => {
        try {
            await sendFeedback(id, type);
            setHistoryItems(prev => prev.map(item =>
                item.id === id ? { ...item, feedback: type } : item
            ));
        } catch (error) {
            alert("피드백 전송에 실패했습니다.");
        }
    };

    if (loading) return <div className="history-loading">기록을 불러오는 중...</div>;

    return (
        <div className="history-container">
            <h2 className="history-title">대화 기록</h2>
            <div className="history-list">
                {historyItems.length === 0 ? (
                    <div className="no-history">대화 기록이 없습니다.</div>
                ) : (
                    currentItems.map(item => (
                        <div key={item.id} className="history-card">
                            <div className="history-header">
                                <span className="history-date">{item.timestamp}</span>
                                <span className={`history-status status-${item.intent === 'transaction' ? 'complete' : 'info'}`}>
                                    {item.intent || '일반'}
                                </span>
                            </div>

                            <div className="history-content">
                                <div className="query-row">
                                    <span className="label">문의:</span>
                                    <span className="value">{item.query}</span>
                                </div>
                                <div className="result-row">
                                    <span className="label">결과:</span>
                                    <span className="value">{item.response}</span>
                                </div>
                            </div>

                            <div className="history-footer">
                                <div className="feedback-section">
                                    <span>만족도 평가: </span>
                                    <button
                                        className={`feedback-btn ${item.feedback === 'good' ? 'active' : ''}`}
                                        onClick={() => handleFeedback(item.id, 'good')}
                                    >
                                        👍 좋음
                                    </button>
                                    <button
                                        className={`feedback-btn ${item.feedback === 'bad' ? 'active' : ''}`}
                                        onClick={() => handleFeedback(item.id, 'bad')}
                                    >
                                        👎 나쁨
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {historyItems.length > ITEMS_PER_PAGE && (
                <div className="pagination-controls">
                    <button
                        className="pagination-btn"
                        onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                        disabled={currentPage === 1}
                    >
                        &lt; 이전
                    </button>
                    <span className="pagination-info">
                        Page {currentPage} of {totalPages}
                    </span>
                    <button
                        className="pagination-btn"
                        onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                        disabled={currentPage === totalPages}
                    >
                        다음 &gt;
                    </button>
                </div>
            )}
        </div>
    );
};

export default History;

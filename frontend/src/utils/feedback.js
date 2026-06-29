export function buildFeedbackFilters({ feedbackFilter, feedbackViewerFilter, feedbackDateFrom, feedbackDateTo, feedbackPage, feedbackRoleFilter, feedbackReviewerFilter }) {
  return {
    resolved: feedbackFilter === 'open' ? false : feedbackFilter === 'resolved' ? true : null,
    search: feedbackViewerFilter || null,
    date_from: feedbackDateFrom || null,
    date_to: feedbackDateTo || null,
    page_number: feedbackPage ? parseInt(feedbackPage, 10) : null,
    author_role: feedbackRoleFilter === 'all' ? null : feedbackRoleFilter,
    reviewer: feedbackReviewerFilter || null,
  };
}

import React from 'react';
import ReactDOM from 'react-dom';
import '@testing-library/jest-dom';

// The source files use `const { useState } = React` (global React pattern from UMD CDN build).
// Make React available globally so all component modules resolve correctly.
global.React = React;
global.ReactDOM = ReactDOM;

// Default no-op SecureDocAPI — individual tests override what they need.
global.window.SecureDocAPI = {
  createLink: async () => ({ share_url: 'https://example.com/view/test-token' }),
  getDocuments: async () => ({ documents: [] }),
  getAnalyticsOverview: async () => ({}),
  getGroups: async () => ({ groups: [] }),
};

import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import CameraWindow from './components/CameraWindow';
import FrontendErrorBoundary from './components/FrontendErrorBoundary';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <FrontendErrorBoundary>{new URLSearchParams(location.search).get('camera')==='1'?<CameraWindow/>:<App/>}</FrontendErrorBoundary>
);

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, theme } from 'antd';
import esES from 'antd/locale/es_ES';
import App from './App.jsx';
import './index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ConfigProvider
      locale={esES}
      theme={{
        // Tema claro y minimalista; azul cielo como color principal
        algorithm: theme.defaultAlgorithm,
        token: { colorPrimary: '#0284c7', borderRadius: 12 },
        components: {
          Table: { headerBg: '#f8fafc' },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </StrictMode>,
);

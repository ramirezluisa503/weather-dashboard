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
        algorithm: theme.darkAlgorithm,
        token: { colorPrimary: '#38bdf8', borderRadius: 12 },
        // La tabla oscura de Ant Design trae fondo sólido: la hacemos transparente para que combine con el vidrio
        components: {
          Table: {
            colorBgContainer: 'transparent',
            headerBg: 'rgba(255, 255, 255, 0.08)',
            rowHoverBg: 'rgba(255, 255, 255, 0.06)',
            borderColor: 'rgba(255, 255, 255, 0.12)',
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </StrictMode>,
);

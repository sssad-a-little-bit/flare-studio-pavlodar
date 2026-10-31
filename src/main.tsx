import { StrictMode, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { Batyr } from './pages/Batyr';
import Picasso from './pages/Picasso';
import { batyr, picasso } from './config';
import '@fontsource-variable/manrope';
import '@fontsource-variable/golos-text';
import './styles/base.css';
import './styles/batyr.css';
import './styles/picasso.css';

function App() {
  const isPicasso = window.location.pathname.replace(/\/$/, '').endsWith('/picasso');
  useEffect(() => {
    document.title = isPicasso ? picasso.title : batyr.title;
    const theme = document.querySelector('meta[name="theme-color"]');
    theme?.setAttribute('content', isPicasso ? '#f6f1e7' : '#17191c');
    const description = document.querySelector('meta[name="description"]');
    description?.setAttribute('content', isPicasso ? `${picasso.name} — демонстрационный концепт детской творческой студии в Павлодаре от Flare Studio.` : `${batyr.name} — демонстрационный концепт автомобильной студии в Павлодаре от Flare Studio.`);
  }, [isPicasso]);
  return isPicasso ? <Picasso /> : <Batyr />;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);




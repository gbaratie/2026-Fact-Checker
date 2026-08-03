import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { CandidateDetailPage } from './pages/CandidateDetailPage';
import { CandidatesPage } from './pages/CandidatesPage';
import { GroupDetailPage, GroupsPage } from './pages/GroupsPage';
import { HomePage } from './pages/HomePage';
import { IngestionPage } from './pages/IngestionPage';
import { PartiesPage, PartyDetailPage } from './pages/PartiesPage';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '') || undefined}>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/candidates" element={<CandidatesPage />} />
          <Route path="/candidates/:slug" element={<CandidateDetailPage />} />
          <Route path="/groups" element={<GroupsPage />} />
          <Route path="/groups/:slug" element={<GroupDetailPage />} />
          <Route path="/parties" element={<PartiesPage />} />
          <Route path="/parties/:party" element={<PartyDetailPage />} />
          <Route path="/ingestion" element={<IngestionPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  </StrictMode>
);

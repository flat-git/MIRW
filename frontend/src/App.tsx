import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DataSourcePage from './pages/DataSourcePage';
import DatasetOverview from './pages/DatasetOverview';
import LossDashboard from './pages/LossDashboard';
import EventsPage from './pages/EventsPage';
import SimilarEventsPage from './pages/SimilarEventsPage';
import ReportPage from './pages/ReportPage';
import ActionTrackerPage from './pages/ActionTrackerPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DataSourcePage />} />
          <Route path="/datasets/:datasetId" element={<DatasetOverview />} />
          <Route path="/datasets/:datasetId/loss" element={<LossDashboard />} />
          <Route path="/datasets/:datasetId/events" element={<EventsPage />} />
          <Route path="/datasets/:datasetId/similar" element={<SimilarEventsPage />} />
          <Route path="/datasets/:datasetId/reports" element={<ReportPage />} />
          <Route path="/datasets/:datasetId/actions" element={<ActionTrackerPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

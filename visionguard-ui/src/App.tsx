/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import HistoricalClaimsExplorer from './pages/HistoricalClaimsExplorer';
import ClaimInvestigationView from './pages/ClaimInvestigationView';
import ProviderIntelligence from './pages/ProviderIntelligence';
import NewClaimScoring from './pages/NewClaimScoring';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ExecutiveDashboard />} />
          <Route path="claims" element={<HistoricalClaimsExplorer />} />
          <Route path="claims/:id" element={<ClaimInvestigationView />} />
          <Route path="providers" element={<ProviderIntelligence />} />
          <Route path="scoring" element={<NewClaimScoring />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

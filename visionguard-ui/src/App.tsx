/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import NewClaimScoring from './pages/NewClaimScoring';

export default function App() {
  return (
    <div className="relative h-screen w-full overflow-y-auto bg-[#05070a] px-4 py-6 text-slate-300 font-sans sm:px-6 lg:px-8">
      <div className="pointer-events-none fixed inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(#00f2ff 1px, transparent 1px)', backgroundSize: '32px 32px' }} />
      <div className="relative z-10">
        <NewClaimScoring />
      </div>
    </div>
  );
}

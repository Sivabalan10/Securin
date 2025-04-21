import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

function App() {
  return (
    <Router>
      <div style={{ height: '100vh', margin: 0 }}>
        <Routes>
          <Route path="/" element={<iframe src="/main.html" width="100%" height="100%" />} />
          {/* <Route path="/contact" element={<iframe src="/contact.html" width="100%" height="100%" />} />  */}
        </Routes>
      </div>
    </Router>
  );
}

export default App;

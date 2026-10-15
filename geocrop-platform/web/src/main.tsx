import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { Protocol } from "pmtiles";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import SiteLayout, { RequireAuth } from "./components/SiteLayout";
import Analyze from "./pages/Analyze";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import LiveMap from "./pages/LiveMap";
import Login from "./pages/Login";
import Models from "./pages/Models";
import Processing from "./pages/Processing";
import Status from "./pages/Status";
import "./styles.css";

// MapLibre 6 loads its worker from a separate file; point it at the bundled asset.
maplibregl.setWorkerUrl(workerUrl);

// Vector layers are PMTiles files read straight from object storage with range requests.
maplibregl.addProtocol("pmtiles", new Protocol().tile);

const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Full-screen map workspace, like the original prototype's Live Map */}
          <Route path="/map" element={<RequireAuth><LiveMap /></RequireAuth>} />
          <Route element={<SiteLayout />}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login mode="login" />} />
            <Route path="/signup" element={<Login mode="signup" />} />
            <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
            <Route path="/analyze" element={<RequireAuth><Analyze /></RequireAuth>} />
            <Route path="/processing/:jobId" element={<RequireAuth><Processing /></RequireAuth>} />
            <Route path="/models" element={<Models />} />
            <Route path="/status" element={<Status />} />
            <Route path="/upload" element={<Navigate to="/analyze" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);

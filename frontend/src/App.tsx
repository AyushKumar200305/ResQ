import React from "react";
import { AppProvider, useApp } from "./context/AppContext";
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { Breadcrumb } from "./components/layout/Breadcrumb";
import { AlertBanner } from "./components/common/AlertBanner";
import { PresentationModal } from "./components/common/PresentationModal";
import { LexiconModal } from "./components/common/LexiconModal";

// Page Components
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { EvacuationPrioritiesPage } from "./pages/EvacuationPrioritiesPage";
import { RoutesAndSheltersPage } from "./pages/RoutesAndSheltersPage";
import { CampResourcesPage } from "./pages/CampResourcesPage";
import { NetworkBuilderPage } from "./pages/NetworkBuilderPage";
import { SimulationPage } from "./pages/SimulationPage";
import { FlowAnalysisPage } from "./pages/FlowAnalysisPage";
import { BottleneckPage } from "./pages/BottleneckPage";
import { ScenarioLabPage } from "./pages/ScenarioLabPage";
import { AlgorithmComparisonPage } from "./pages/AlgorithmComparisonPage";
import { AlgorithmAnalysisPage } from "./pages/AlgorithmAnalysisPage";
import { ReportsPage } from "./pages/ReportsPage";
import { AboutPage } from "./pages/AboutPage";

const MainLayout: React.FC = () => {
  const { activePage, isPresentationOpen, closePresentation, isLexiconOpen, closeLexicon } = useApp();

  // Standalone full-screen pages
  if (activePage === "landing") {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
        <LandingPage />
        <AlertBanner />
      </div>
    );
  }

  if (activePage === "login") {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
        <LoginPage />
        <AlertBanner />
      </div>
    );
  }

  // Application Dashboard Shell
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 space-y-6 bg-slate-50">
          <Breadcrumb />

          <div className="max-w-7xl mx-auto pb-12">
            {activePage === "overview" && <OverviewPage />}
            {activePage === "priorities" && <EvacuationPrioritiesPage />}
            {activePage === "routes" && <RoutesAndSheltersPage />}
            {activePage === "resources" && <CampResourcesPage />}
            {activePage === "builder" && <NetworkBuilderPage />}
            {activePage === "simulation" && <SimulationPage />}
            {activePage === "flow" && <FlowAnalysisPage />}
            {activePage === "bottlenecks" && <BottleneckPage />}
            {activePage === "scenarios" && <ScenarioLabPage />}
            {activePage === "compare" && <AlgorithmComparisonPage />}
            {activePage === "dijkstra" && <AlgorithmAnalysisPage defaultTab="dijkstra" />}
            {activePage === "algorithms" && <AlgorithmAnalysisPage />}
            {activePage === "reports" && <ReportsPage />}
            {activePage === "about" && <AboutPage />}
          </div>
        </main>
      </div>

      <AlertBanner />
      <PresentationModal isOpen={isPresentationOpen} onClose={closePresentation} />
      <LexiconModal isOpen={isLexiconOpen} onClose={closeLexicon} />
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <MainLayout />
    </AppProvider>
  );
}

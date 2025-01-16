import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import Navigation from './components/Navigation';
import Layout from './components/Layout';
import Installation from './pages/installation.md';
import Modules from './pages/modules.md';
import Configuration from './pages/configuration.md';
import API from './pages/api.md';

const App: React.FC = () => {
    return (
        <Router>
            <Layout>
                <Navigation />
                <Switch>
                    <Route path="/installation" component={Installation} />
                    <Route path="/modules" component={Modules} />
                    <Route path="/configuration" component={Configuration} />
                    <Route path="/api" component={API} />
                </Switch>
            </Layout>
        </Router>
    );
};

export default App;
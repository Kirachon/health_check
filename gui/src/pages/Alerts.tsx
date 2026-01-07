import React from 'react';
import { AlertTriangle } from 'lucide-react';
import PlaceholderPage from './PlaceholderPage';

const Alerts: React.FC = () => {
    return (
        <PlaceholderPage
            title="Problem Management"
            icon={AlertTriangle}
            description="Real-time alerting and incident management system. Advanced trigger expressions and correlation rules will be configurable here."
        />
    );
};

export default Alerts;

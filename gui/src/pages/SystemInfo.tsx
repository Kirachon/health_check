import React from 'react';
import { Activity } from 'lucide-react';
import PlaceholderPage from './PlaceholderPage';

const SystemInfo: React.FC = () => {
    return (
        <PlaceholderPage
            title="System Information"
            icon={Activity}
            description="Detailed health overview of the monitoring server and ingestion cluster. Monitor throughput, latency, and resource health."
        />
    );
};

export default SystemInfo;

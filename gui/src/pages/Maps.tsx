import React from 'react';
import { Map } from 'lucide-react';
import PlaceholderPage from './PlaceholderPage';

const Maps: React.FC = () => {
    return (
        <PlaceholderPage
            title="Network Topology Maps"
            icon={Map}
            description="Visual representation of your network infrastructure. Interactive topology views and status overlays are coming soon."
        />
    );
};

export default Maps;

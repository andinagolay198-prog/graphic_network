import React, { useState, useEffect, useRef } from 'react';
import { Search, Zap, WifiOff, Eye, EyeOff, Download, RefreshCw } from 'lucide-react';

const NetworkTopologyManager = () => {
  const canvasRef = useRef(null);
  const [devices, setDevices] = useState([]);
  const [links, setLinks] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('physical'); // physical, logical, tunnel
  const [showLabels, setShowLabels] = useState(true);
  const [autoLayout, setAutoLayout] = useState(true);
  const [filter, setFilter] = useState('all'); // all, up, down
  const [draggedDevice, setDraggedDevice] = useState(null);
  const [devicePositions, setDevicePositions] = useState({});

  // Sample data - trong production sẽ lấy từ backend API
  const TOPOLOGY_URL = 'http://localhost:8000';

  const fetchTopology = async () => {
    try {
      const r = await fetch(`${TOPOLOGY_URL}/api/topology`);
      const data = await r.json();
      const devs = data.devices || [];
      setDevices(devs);
      setLinks(data.links || []);
      const positions = {};
      devs.forEach((device, index) => {
        const angle = (index / Math.max(devs.length,1)) * 2 * Math.PI;
        const radius = 200;
        positions[device.id] = {
          x: 400 + radius * Math.cos(angle),
          y: 300 + radius * Math.sin(angle),
        };
      });
      setDevicePositions(positions);
    } catch(e) { console.error('Fetch error:', e); }
  };

  useEffect(() => {
    fetchTopology();
    const timer = setInterval(fetchTopology, 30000);
    return () => clearInterval(timer);
  }, []);

  // Filter devices
  const filteredDevices = devices.filter(device => {
    const matchSearch = device.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                       device.ip.includes(searchTerm);
    const matchStatus = filter === 'all' || device.status === filter;
    return matchSearch && matchStatus;
  });

  // Get links untuk filtered devices
  const filteredLinks = links.filter(link => {
    const fromVisible = filteredDevices.some(d => d.id === link.from);
    const toVisible = filteredDevices.some(d => d.id === link.to);
    return fromVisible && toVisible;
  });

  // Draw canvas
  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    for (let i = 0; i < canvas.width; i += 50) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, canvas.height);
      ctx.stroke();
    }
    for (let i = 0; i < canvas.height; i += 50) {
      ctx.beginPath();
      ctx.moveTo(0, i);
      ctx.lineTo(canvas.width, i);
      ctx.stroke();
    }

    // Draw links
    filteredLinks.forEach(link => {
      const fromPos = devicePositions[link.from];
      const toPos = devicePositions[link.to];
      
      if (!fromPos || !toPos) return;

      // Link style
      if (link.type === 'tunnel') {
        ctx.strokeStyle = '#6366f1'; // Indigo for tunnels
        ctx.setLineDash([5, 5]);
        ctx.lineWidth = 3;
      } else if (link.status === 'inactive') {
        ctx.strokeStyle = '#ef4444'; // Red
        ctx.setLineDash([]);
        ctx.lineWidth = 2;
      } else {
        ctx.strokeStyle = '#10b981'; // Green
        ctx.setLineDash([]);
        ctx.lineWidth = 2;
      }

      ctx.beginPath();
      ctx.moveTo(fromPos.x, fromPos.y);
      ctx.lineTo(toPos.x, toPos.y);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw bandwidth label
      if (showLabels) {
        const midX = (fromPos.x + toPos.x) / 2;
        const midY = (fromPos.y + toPos.y) / 2;
        ctx.fillStyle = '#374151';
        ctx.font = '12px Arial';
        ctx.fillText(link.bandwidth, midX + 5, midY - 5);
      }
    });

    // Draw devices
    filteredDevices.forEach(device => {
      const pos = devicePositions[device.id];
      if (!pos) return;

      // Device circle
      const radius = 35;
      const isSelected = selectedDevice?.id === device.id;

      // Background circle
      ctx.fillStyle = isSelected ? '#fbbf24' : '#ffffff';
      ctx.strokeStyle = device.status === 'up' ? '#10b981' : '#ef4444';
      ctx.lineWidth = isSelected ? 4 : 3;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();

      // Status indicator (small dot)
      ctx.fillStyle = device.status === 'up' ? '#10b981' : '#ef4444';
      ctx.beginPath();
      ctx.arc(pos.x + 25, pos.y - 20, 8, 0, 2 * Math.PI);
      ctx.fill();

      // Device icon/type
      ctx.fillStyle = '#1f2937';
      ctx.font = 'bold 18px Arial';
      const iconMap = {
        router: '🌐',
        firewall: '🔒',
        switch: '⚡',
        ap: '📶',
        modem: '📡',
      };
      ctx.fillText(iconMap[device.type] || '🖥️', pos.x - 9, pos.y + 6);

      // Device name label
      if (showLabels) {
        ctx.fillStyle = '#1f2937';
        ctx.font = '11px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(device.name, pos.x, pos.y + 50);
        ctx.fillText(device.ip, pos.x, pos.y + 65);
      }
    });
  }, [devicePositions, filteredDevices, filteredLinks, selectedDevice, showLabels]);

  // Handle canvas click
  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    for (let device of filteredDevices) {
      const pos = devicePositions[device.id];
      const distance = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
      if (distance < 40) {
        setSelectedDevice(device);
        return;
      }
    }
    setSelectedDevice(null);
  };

  // Handle device drag
  const handleCanvasMouseDown = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    for (let device of filteredDevices) {
      const pos = devicePositions[device.id];
      const distance = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
      if (distance < 40) {
        setDraggedDevice(device);
        return;
      }
    }
  };

  const handleCanvasMouseMove = (e) => {
    if (!draggedDevice) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setDevicePositions({
      ...devicePositions,
      [draggedDevice.id]: { x, y },
    });
  };

  const handleCanvasMouseUp = () => {
    setDraggedDevice(null);
  };

  const exportTopology = () => {
    const data = {
      devices: devices,
      links: links,
      positions: devicePositions,
      exportTime: new Date().toISOString(),
    };
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'network-topology.json';
    a.click();
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Sidebar - Device List */}
      <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto shadow-sm">
        <div className="p-4 border-b border-gray-200 sticky top-0 bg-white">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Network Topology</h2>
          
          {/* Search */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search device..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Filter Tabs */}
          <div className="flex gap-2 mb-3">
            {['all', 'up', 'down'].map(status => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  filter === status
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {status === 'all' ? 'All' : status.toUpperCase()}
              </button>
            ))}
          </div>

          {/* View Mode */}
          <div className="flex gap-2">
            {['physical', 'logical', 'tunnel'].map(mode => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`flex-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                  viewMode === mode
                    ? 'bg-indigo-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                title={mode === 'tunnel' ? 'Show tunnel links only' : ''}
              >
                {mode.slice(0, 3).toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Device List */}
        <div className="p-4">
          {filteredDevices.map(device => (
            <div
              key={device.id}
              onClick={() => setSelectedDevice(device)}
              className={`mb-3 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                selectedDevice?.id === device.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 text-sm">{device.name}</h3>
                  <p className="text-xs text-gray-500 mt-1">{device.ip}</p>
                  <div className="flex gap-2 mt-2">
                    <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                      {device.type}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded font-medium ${
                      device.status === 'up'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {device.status.toUpperCase()}
                    </span>
                  </div>
                </div>
                <div className="ml-2">
                  {device.status === 'up' ? (
                    <Zap className="w-5 h-5 text-green-500" />
                  ) : (
                    <WifiOff className="w-5 h-5 text-red-500" />
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="bg-white border-b border-gray-200 p-4 flex justify-between items-center shadow-sm">
          <div className="flex gap-2">
            <button
              onClick={() => setShowLabels(!showLabels)}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors"
            >
              {showLabels ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              {showLabels ? 'Hide' : 'Show'} Labels
            </button>
            
            <button
              onClick={exportTopology}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
            </button>

            <button
              onClick={() => {}}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          <div className="text-xs text-gray-500">
            Devices: {filteredDevices.length} | Links: {filteredLinks.length}
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 relative">
          <canvas
            ref={canvasRef}
            width={1200}
            height={700}
            onClick={handleCanvasClick}
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
            onMouseLeave={handleCanvasMouseUp}
            className="w-full h-full cursor-grab active:cursor-grabbing"
          />
        </div>
      </div>

      {/* Right Sidebar - Device Details */}
      {selectedDevice && (
        <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto shadow-sm">
          <div className="p-4 border-b border-gray-200 flex justify-between items-center sticky top-0 bg-white">
            <h3 className="font-bold text-gray-900">Device Details</h3>
            <button
              onClick={() => setSelectedDevice(null)}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>

          <div className="p-4">
            {/* Device Header */}
            <div className="mb-6 p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg">
              <h4 className="text-lg font-bold text-gray-900">{selectedDevice.name}</h4>
              <p className="text-sm text-gray-600 mt-2">{selectedDevice.ip}</p>
              <div className="mt-3 flex gap-2">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                  {selectedDevice.type.toUpperCase()}
                </span>
                <span className={`px-3 py-1 rounded text-xs font-medium ${
                  selectedDevice.status === 'up'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}>
                  {selectedDevice.status.toUpperCase()}
                </span>
              </div>
            </div>

            {/* Device Info */}
            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase">Vendor</label>
                <p className="text-gray-900 font-medium">{selectedDevice.vendor}</p>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase">Connected Links</label>
                <div className="mt-2 space-y-2">
                  {filteredLinks
                    .filter(l => l.from === selectedDevice.id || l.to === selectedDevice.id)
                    .map((link, idx) => (
                      <div key={idx} className="p-2 bg-gray-50 rounded border border-gray-200">
                        <p className="text-xs font-medium text-gray-700">
                          {link.from === selectedDevice.id ? '→' : '←'} {
                            devices.find(d => d.id === (link.from === selectedDevice.id ? link.to : link.from))?.name
                          }
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          {link.bandwidth} • {link.type === 'tunnel' ? '🔐 Tunnel' : '⚡ Wired'}
                        </p>
                      </div>
                    ))}
                </div>
              </div>

              {/* Metrics Preview */}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase">Real-time Metrics</label>
                <div className="mt-2 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">CPU Usage</span>
                    <span className="text-sm font-semibold text-gray-900">45%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-orange-500 h-2 rounded-full" style={{ width: '45%' }} />
                  </div>
                </div>
                <div className="mt-3 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Memory Usage</span>
                    <span className="text-sm font-semibold text-gray-900">62%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-red-500 h-2 rounded-full" style={{ width: '62%' }} />
                  </div>
                </div>
                <div className="mt-3 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Uptime</span>
                    <span className="text-sm font-semibold text-gray-900">98.5%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-green-500 h-2 rounded-full" style={{ width: '98.5%' }} />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="pt-4 border-t border-gray-200">
                <button className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 transition-colors mb-2">
                  View Details
                </button>
                <button className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-lg font-medium hover:bg-gray-200 transition-colors">
                  SSH Terminal
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NetworkTopologyManager;

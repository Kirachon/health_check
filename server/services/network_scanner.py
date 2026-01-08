"""Network scanner service for device discovery."""
import asyncio
import ipaddress
import logging
import socket
import json
import subprocess
import platform
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from db.models import DiscoveryJob, DiscoveryResult, Device

logger = logging.getLogger(__name__)

# Default ports to scan
DEFAULT_PORTS = [22, 23, 80, 443, 161, 8080, 3389]


class NetworkScanner:
    """Network discovery scanner with ICMP ping sweep, port scanning, and SNMP detection."""
    
    def __init__(self):
        self.is_windows = platform.system().lower() == 'windows'

    def _is_valid_ip(self, ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    async def ping_host(self, ip: str, timeout: int = 1) -> Dict[str, Any]:
        """
        Ping a single host and return reachability info.
        
        Returns:
            Dict with 'reachable' and 'latency_ms' keys
        """
        result = {'reachable': False, 'latency_ms': None}
        
        if not self._is_valid_ip(ip):
            logger.debug(f"Skipping ping for invalid IP: {ip}")
            return result

        try:
            # Platform-specific ping command
            if self.is_windows:
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), ip]
            
            start_time = asyncio.get_event_loop().time()
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 2)
            
            end_time = asyncio.get_event_loop().time()
            
            if proc.returncode == 0:
                result['reachable'] = True
                result['latency_ms'] = int((end_time - start_time) * 1000)
                
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"Ping failed for {ip}: {e}")
        
        return result
    
    async def resolve_hostname(self, ip: str) -> Optional[str]:
        """Attempt to resolve hostname from IP via reverse DNS."""
        try:
            hostname, _, _ = await asyncio.get_event_loop().run_in_executor(
                None, socket.gethostbyaddr, ip
            )
            return hostname
        except (socket.herror, socket.gaierror):
            return None
    
    async def check_port(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a TCP port is open."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
    
    async def scan_ports(self, ip: str, ports: List[int] = None) -> Dict[str, str]:
        """
        Scan multiple ports on a host.
        
        Returns:
            Dict mapping port number (str) to service name
        """
        if ports is None:
            ports = DEFAULT_PORTS
        
        open_ports = {}
        
        # Scan ports concurrently (limit concurrency)
        sem = asyncio.Semaphore(10)
        
        async def check_with_sem(port):
            async with sem:
                if await self.check_port(ip, port):
                    service = self._get_service_name(port)
                    return (str(port), service)
            return None
        
        results = await asyncio.gather(*[check_with_sem(p) for p in ports])
        
        for r in results:
            if r:
                open_ports[r[0]] = r[1]
        
        return open_ports
    
    def _get_service_name(self, port: int) -> str:
        """Get common service name for a port."""
        services = {
            22: 'ssh',
            23: 'telnet',
            80: 'http',
            443: 'https',
            161: 'snmp',
            3389: 'rdp',
            8080: 'http-alt',
            8443: 'https-alt',
            5432: 'postgresql',
            3306: 'mysql',
        }
        return services.get(port, 'unknown')
    
    async def snmp_get(self, ip: str, community: str = 'public', oid: str = '1.3.6.1.2.1.1.1.0') -> Optional[str]:
        """
        Simple SNMP GET using snmpget command (if available).
        For production, use pysnmp library.
        """
        try:
            cmd = ['snmpget', '-v', '2c', '-c', community, '-t', '2', ip, oid]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            
            if proc.returncode == 0:
                return stdout.decode().strip()
            return None
        except Exception as e:
            logger.debug(f"SNMP failed for {ip}: {e}")
            return None
    
    def parse_cidr_ranges(self, ip_ranges: str) -> List[ipaddress.IPv4Network]:
        """
        Parse comma-separated CIDR ranges into network objects.
        
        Args:
            ip_ranges: e.g., "192.168.1.0/24,10.0.0.0/8"
            
        Returns:
            List of IPv4Network objects
        """
        networks = []
        for range_str in ip_ranges.split(','):
            range_str = range_str.strip()
            if range_str:
                try:
                    network = ipaddress.ip_network(range_str, strict=False)
                    networks.append(network)
                except ValueError as e:
                    logger.warning(f"Invalid CIDR range '{range_str}': {e}")
        return networks
    
    def get_hosts_from_ranges(self, ip_ranges: str, max_hosts: int = 10000) -> List[str]:
        """
        Get list of host IPs from CIDR ranges.
        
        Args:
            ip_ranges: Comma-separated CIDR notation
            max_hosts: Maximum hosts to scan (safety limit)
            
        Returns:
            List of IP address strings
        """
        hosts = []
        networks = self.parse_cidr_ranges(ip_ranges)
        
        for network in networks:
            for host in network.hosts():
                if len(hosts) >= max_hosts:
                    logger.warning(f"Host limit reached ({max_hosts}), truncating scan")
                    return hosts
                hosts.append(str(host))
        
        return hosts
    
    async def scan_host(
        self, 
        ip: str, 
        scan_icmp: bool = True,
        scan_snmp: bool = False,
        snmp_community: str = 'public',
        scan_ports_list: List[int] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive scan of a single host.
        
        Returns:
            Dict with all scan results
        """
        result = {
            'ip_address': ip,
            'hostname': None,
            'icmp_reachable': None,
            'icmp_latency_ms': None,
            'snmp_reachable': None,
            'snmp_sysname': None,
            'snmp_sysdescr': None,
            'open_ports': None
        }

        if not self._is_valid_ip(ip):
            logger.debug(f"Skipping scan for invalid IP: {ip}")
            return result
        
        # ICMP ping
        if scan_icmp:
            ping_result = await self.ping_host(ip)
            result['icmp_reachable'] = ping_result['reachable']
            result['icmp_latency_ms'] = ping_result['latency_ms']
        
        # Only continue if host is reachable (or not scanning ICMP)
        if result.get('icmp_reachable') or not scan_icmp:
            # Hostname resolution
            result['hostname'] = await self.resolve_hostname(ip)
            
            # Port scan
            if scan_ports_list:
                open_ports = await self.scan_ports(ip, scan_ports_list)
                if open_ports:
                    result['open_ports'] = json.dumps(open_ports)
            
            # SNMP scan
            if scan_snmp:
                # sysDescr
                sysdescr = await self.snmp_get(ip, snmp_community, '1.3.6.1.2.1.1.1.0')
                if sysdescr:
                    result['snmp_reachable'] = True
                    result['snmp_sysdescr'] = sysdescr
                    
                    # sysName
                    sysname = await self.snmp_get(ip, snmp_community, '1.3.6.1.2.1.1.5.0')
                    if sysname:
                        result['snmp_sysname'] = sysname.split('=')[-1].strip() if '=' in sysname else sysname
                else:
                    result['snmp_reachable'] = False
        
        return result
    
    async def run_discovery(
        self,
        job: DiscoveryJob,
        db: Session,
        progress_callback=None
    ) -> List[DiscoveryResult]:
        """
        Run a full discovery job.
        
        Args:
            job: DiscoveryJob to execute
            db: Database session
            progress_callback: Optional callback(percent, message)
            
        Returns:
            List of DiscoveryResult objects created
        """
        logger.info(f"Starting discovery job '{job.name}' for ranges: {job.ip_ranges}")
        
        # Get host list
        hosts = self.get_hosts_from_ranges(job.ip_ranges)
        total_hosts = len(hosts)
        
        if total_hosts == 0:
            logger.warning("No hosts to scan")
            return []
        
        # Parse port list
        scan_ports = None
        if job.scan_ports:
            scan_ports = [int(p.strip()) for p in job.scan_ports.split(',') if p.strip().isdigit()]
        
        # Update job status
        job.status = 'running'
        job.started_at = datetime.utcnow()
        job.progress_percent = 0
        db.commit()
        
        results = []
        scanned = 0
        
        # Scan hosts with concurrency limit
        sem = asyncio.Semaphore(50)  # Max 50 concurrent scans
        
        async def scan_with_progress(ip: str) -> Optional[DiscoveryResult]:
            nonlocal scanned
            async with sem:
                try:
                    scan_result = await self.scan_host(
                        ip,
                        scan_icmp=job.scan_icmp,
                        scan_snmp=job.scan_snmp,
                        snmp_community=job.snmp_community or 'public',
                        scan_ports_list=scan_ports
                    )
                    
                    # Only save if host responded
                    if scan_result.get('icmp_reachable') or scan_result.get('snmp_reachable'):
                        # Check if device already exists
                        existing_device = db.query(Device).filter(
                            Device.ip_address == ip
                        ).first()
                        
                        discovery_result = DiscoveryResult(
                            job_id=job.id,
                            ip_address=ip,
                            hostname=scan_result.get('hostname'),
                            icmp_reachable=scan_result.get('icmp_reachable'),
                            icmp_latency_ms=scan_result.get('icmp_latency_ms'),
                            snmp_reachable=scan_result.get('snmp_reachable'),
                            snmp_sysname=scan_result.get('snmp_sysname'),
                            snmp_sysdescr=scan_result.get('snmp_sysdescr'),
                            open_ports=scan_result.get('open_ports'),
                            status='existing' if existing_device else 'new',
                            device_id=existing_device.id if existing_device else None
                        )
                        db.add(discovery_result)
                        return discovery_result
                    return None
                    
                except Exception as e:
                    logger.error(f"Error scanning {ip}: {e}")
                    return None
                finally:
                    scanned += 1
                    pct = int((scanned / total_hosts) * 100)
                    if pct != job.progress_percent:
                        job.progress_percent = pct
                        db.commit()
                        if progress_callback:
                            progress_callback(pct, f"Scanned {scanned}/{total_hosts}")
        
        # Run all scans
        try:
            scan_tasks = [scan_with_progress(ip) for ip in hosts]
            scan_results = await asyncio.gather(*scan_tasks)
            
            results = [r for r in scan_results if r is not None]
            
            # Update job status
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress_percent = 100
            db.commit()
            
            logger.info(f"Discovery job '{job.name}' completed: {len(results)} hosts found")
            
            return results
        except Exception as e:
            db.rollback()
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
            logger.error(f"Discovery job '{job.name}' failed: {e}")
            raise


# Singleton instance
network_scanner = NetworkScanner()

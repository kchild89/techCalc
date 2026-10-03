"""Curated, copy-only command reference. Commands are never executed by the hub."""
import ipaddress
import re

TOOLS = {
    "Nmap": {
        "category": "Network discovery", "platform": "Windows, Linux, macOS",
        "about": "Map reachable hosts and exposed services. Useful for an authorized asset inventory and verifying firewall changes.",
        "setup": "Install Nmap from nmap.org; Windows packet features may also require Npcap. TCP connect examples work without raw-socket privileges.",
        "docs": "https://nmap.org/book/man.html", "download": "https://nmap.org/download.html"},
    "Wireshark / TShark": {
        "category": "Packet analysis", "platform": "Windows, Linux, macOS",
        "about": "Wireshark is a graphical packet analyzer; TShark is its command-line companion. These examples inspect captures you already have.",
        "setup": "Install Wireshark with the TShark component. Put a capture named capture.pcapng in your working folder.",
        "docs": "https://www.wireshark.org/docs/man-pages/tshark.html", "download": "https://www.wireshark.org/download.html"},
    "curl": {
        "category": "HTTP diagnostics", "platform": "Windows; use curl instead of curl.exe on Linux/macOS",
        "about": "Inspect HTTP responses, redirect behavior, and TLS connection details from a terminal.",
        "setup": "Modern Windows includes curl.exe. The .exe suffix avoids the curl alias in older Windows PowerShell.",
        "docs": "https://curl.se/docs/manpage.html", "download": "https://curl.se/download.html"},
    "OpenSSL": {
        "category": "TLS and certificates", "platform": "Windows, Linux, macOS",
        "about": "Examine certificates, diagnose TLS handshakes, and hash local evidence files.",
        "setup": "Use an OpenSSL installation from your OS package source or the project's distribution guidance. The certificate example expects cert.pem.",
        "docs": "https://docs.openssl.org/3.6/man1/", "download": "https://www.openssl.org/source/"},
    "dig": {
        "category": "DNS diagnostics", "platform": "Linux/macOS; BIND utilities or WSL on Windows",
        "about": "Query DNS records to understand resolution, mail routing, and authoritative name servers.",
        "setup": "Install your platform's BIND DNS utilities. Use a hostname in the target field.",
        "docs": "https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility", "download": "https://www.isc.org/bind/"},
    "tcpdump": {
        "category": "Packet analysis", "platform": "Linux, macOS, Unix / WSL",
        "about": "A compact command-line packet reader. Offline capture filtering helps isolate conversations before deeper investigation.",
        "setup": "Install tcpdump through your OS package manager. These recipes read capture.pcap and do not start live capture.",
        "docs": "https://www.tcpdump.org/manpages/tcpdump.1.html", "download": "https://www.tcpdump.org/"},
    "YARA": {
        "category": "File triage", "platform": "Windows, Linux, macOS",
        "about": "Match files against rules describing strings and byte patterns. A match is an investigative lead, not a verdict.",
        "setup": "Install YARA and supply a source rule file named rules.yar plus a samples directory. On Windows the executable may be yara64.exe.",
        "docs": "https://yara.readthedocs.io/en/stable/commandline.html", "download": "https://github.com/VirusTotal/yara/releases"},
    "PowerShell": {
        "category": "Windows diagnostics", "platform": "Windows PowerShell / PowerShell 7 on Windows",
        "about": "Inspect connections, event logs, and file hashes using built-in Windows commands.",
        "setup": "Open PowerShell. Some event logs and process details need an elevated session. Examples read local state.",
        "docs": "https://learn.microsoft.com/en-us/powershell/", "download": "https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows"},
    "Sysinternals": {
        "category": "Windows diagnostics", "platform": "Windows",
        "about": "Microsoft's advanced Windows troubleshooting utilities, including Sigcheck and Sysmon.",
        "setup": "Download the relevant utility from Microsoft Sysinternals. Sysmon queries require an existing Sysmon installation.",
        "docs": "https://learn.microsoft.com/en-us/sysinternals/", "download": "https://learn.microsoft.com/en-us/sysinternals/downloads/"},
    "jq": {
        "category": "Structured data", "platform": "Windows, Linux, macOS",
        "about": "Filter and summarize JSON evidence, API output, and downloaded threat-intelligence catalogs.",
        "setup": "Install jq. Catalog recipes expect a locally downloaded CISA JSON file named kev.json.",
        "docs": "https://jqlang.org/manual/", "download": "https://jqlang.org/download/"},
}


def recipe(key, tool, title, command, purpose, flags, output, note="", docs=None):
    return {"id": key, "tool": tool, "title": title, "command": command,
            "purpose": purpose, "flags": flags, "output": output, "note": note,
            "docs": docs or TOOLS[tool]["docs"]}


RECIPES = [
    recipe("nmap-discover", "Nmap", "Find reachable hosts", "nmap -sn {host}",
           "Check which addresses respond before building a service inventory.",
           "-sn: host discovery without a port scan.",
           "Responsive addresses and any available host names.",
           "A missing reply does not prove a host is absent; firewalls can block discovery.",
           "https://nmap.org/book/man-host-discovery.html"),
    recipe("nmap-tcp", "Nmap", "Check selected TCP ports", "nmap -sT -p {ports} --reason {host}",
           "Verify a small set of expected services.",
           "-sT: TCP connect scan.  -p: selected ports.  --reason: why each state was assigned.",
           "Ports marked open, closed, or filtered, with reasons.",
           "Use the target and port fields below. Scans generate traffic and may be logged.",
           "https://nmap.org/book/man-briefoptions.html"),
    recipe("nmap-version", "Nmap", "Identify service versions", "nmap -sT -sV --version-light -p {ports} {host}",
           "Gather service identity hints from the ports you selected.",
           "-sV: service probes.  --version-light: a smaller probe set.  -p: constrain the scope.",
           "Service names and available version strings.",
           "A banner alone does not confirm that a particular vulnerability applies.",
           "https://nmap.org/book/man-version-detection.html"),
    recipe("nmap-save", "Nmap", "Save an inventory report", "nmap -sT -p {ports} -oA inventory {host}",
           "Keep a scan result for documentation and later comparison.",
           "-oA inventory: write normal, XML, and grepable output using that base name.",
           "inventory.nmap, inventory.xml, and inventory.gnmap in the current folder.",
           "Choose a new output base name for each run to avoid overwriting an earlier report.",
           "https://nmap.org/book/man-output.html"),
    recipe("nmap-cert", "Nmap", "Inspect a TLS certificate", "nmap -sT -p 443 --script ssl-cert {host}",
           "Read the certificate presented by a TLS service.",
           "--script ssl-cert: certificate inspection.  -p 443: HTTPS port.",
           "Subject, issuer, and certificate validity details.",
           "This describes the certificate presented; it is not a complete TLS security assessment.",
           "https://nmap.org/nsedoc/scripts/ssl-cert.html"),
    recipe("tshark-interfaces", "Wireshark / TShark", "List capture interfaces", "tshark -D",
           "Find available interface names before configuring a capture.",
           "-D: enumerate interfaces and exit.", "Interface numbers and names."),
    recipe("tshark-dns", "Wireshark / TShark", "Review DNS packets", 'tshark -r capture.pcapng -Y "dns"',
           "Isolate DNS traffic from an existing capture.",
           "-r: read a file.  -Y: apply a Wireshark display filter.",
           "Packet summaries for matching DNS traffic."),
    recipe("tshark-fields", "Wireshark / TShark", "Extract DNS query names",
           'tshark -r capture.pcapng -Y "dns.flags.response == 0" -T fields -e frame.time -e ip.src -e dns.qry.name',
           "Produce a compact list of observed DNS questions.",
           "-T fields: field output.  -e: choose fields.  Response flag 0 selects questions.",
           "Time, IPv4 source, and query name. IPv6 packets may have an empty ip.src field."),
    recipe("tshark-conversations", "Wireshark / TShark", "Summarize TCP conversations",
           "tshark -r capture.pcapng -q -z conv,tcp",
           "Identify busy endpoint pairs in a capture.",
           "-q: suppress packet summaries.  -z conv,tcp: TCP conversation statistics.",
           "Endpoint pairs, packets, bytes, and timing."),
    recipe("curl-headers", "curl", "Inspect HTTP headers", "curl.exe --head --max-time 15 https://{host}",
           "Read response headers with a HEAD request.",
           "--head: request headers.  --max-time: total time limit in seconds.",
           "Status and response headers.", "Some servers treat HEAD differently from GET."),
    recipe("curl-redirects", "curl", "Follow a redirect chain",
           "curl.exe --head --location --max-redirs 5 --max-time 20 https://{host}",
           "Check redirects while limiting the number of hops.",
           "--location: follow redirects.  --max-redirs: cap the redirect count.",
           "Headers at each redirect step and the final response."),
    recipe("curl-verbose", "curl", "Diagnose HTTPS negotiation",
           "curl.exe --verbose --head --max-time 15 https://{host}",
           "Inspect connection and TLS details while retaining certificate verification.",
           "--verbose: diagnostic output.  --head: request headers.",
           "TLS negotiation information and HTTP headers.", "Review diagnostics before sharing them; headers may contain sensitive values."),
    recipe("openssl-tls", "OpenSSL", "Verify a TLS host",
           "openssl s_client -connect {host}:443 -servername {host} -verify_hostname {host} -verify_return_error",
           "Inspect a server handshake with an explicit server name and hostname check.",
           "-servername: SNI.  -verify_hostname: expected certificate name.  -verify_return_error: stop on verification failure.",
           "Handshake and certificate-chain results.", "Uses your OpenSSL trust configuration; Ctrl+C ends the interactive connection.",
           "https://docs.openssl.org/3.6/man1/openssl-s_client/"),
    recipe("openssl-cert", "OpenSSL", "Read a local certificate",
           "openssl x509 -in cert.pem -noout -subject -issuer -dates",
           "Extract certificate identity and validity dates.",
           "-in: input PEM file.  -noout: omit encoded certificate data.",
           "Subject, issuer, notBefore, and notAfter.",
           docs="https://docs.openssl.org/3.6/man1/openssl-x509/"),
    recipe("openssl-hash", "OpenSSL", "Hash a local file", "openssl dgst -sha256 evidence.bin",
           "Calculate a reproducible fingerprint for a local file.",
           "-sha256: select SHA-256.", "A SHA-256 digest for evidence.bin.",
           "A matching hash establishes file equality, not that a file is safe.",
           "https://docs.openssl.org/3.6/man1/openssl-dgst/"),
    recipe("dig-a", "dig", "Query IPv4 records", "dig {host} A +noall +answer",
           "Inspect the answer section for a hostname.",
           "A: IPv4 records.  +noall +answer: show only answers.", "Record names, TTLs, and IPv4 addresses."),
    recipe("dig-mx", "dig", "Inspect mail routing", "dig {host} MX +noall +answer",
           "Find mail exchangers advertised by a domain.",
           "MX: mail exchanger records.", "MX priorities and server names."),
    recipe("dig-ns", "dig", "Find authoritative name servers", "dig {host} NS +noall +answer",
           "See the name servers delegated for a domain.",
           "NS: name server records.", "Names of authoritative DNS servers."),
    recipe("tcpdump-read", "tcpdump", "Read capture summaries", "tcpdump -nn -r capture.pcap -c 100",
           "Review the first hundred packets from a local capture.",
           "-nn: numeric hosts and ports.  -r: read a file.  -c: packet limit.",
           "Human-readable packet summaries."),
    recipe("tcpdump-dns", "tcpdump", "Filter DNS traffic", "tcpdump -nn -r capture.pcap port 53",
           "Focus an offline capture on conventional DNS traffic.",
           "port 53: match either source or destination port 53.",
           "Matching packet summaries.", "Encrypted DNS may use other ports and will not be identified by this filter."),
    recipe("tcpdump-host", "tcpdump", "Isolate one host", "tcpdump -nn -r capture.pcap host {host}",
           "Inspect packets to or from one address in a capture.",
           "host: match traffic involving the specified host.",
           "Matching packet summaries.", "Use an IPv4 address to avoid a DNS lookup."),
    recipe("yara-file", "YARA", "Match rules against a file", "yara -s rules.yar sample.bin",
           "Inspect which rule strings match a local file without running the sample.",
           "-s: show matching strings.", "Matching rule names, offsets, and strings.",
           "Use reviewed source rules. An empty result only means those rules did not match."),
    recipe("yara-folder", "YARA", "Triage a sample directory", "yara -r -s -a 30 rules.yar samples",
           "Apply your source rules to a directory tree.",
           "-r: recurse.  -s: show matching strings.  -a 30: scan timeout.",
           "Matches across the directory.",
           "Recursive scans can encounter links; use --no-follow-symlinks when supported and appropriate."),
    recipe("ps-connections", "PowerShell", "Inspect established connections",
           "Get-NetTCPConnection -State Established | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess",
           "Associate current TCP connections with owning process IDs.",
           "-State Established: limit results to connected TCP sessions.",
           "Local and remote endpoints plus the owning PID.",
           docs="https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-nettcpconnection"),
    recipe("ps-hash", "PowerShell", "Hash evidence with SHA-256",
           "Get-FileHash -LiteralPath '.\\evidence.bin' -Algorithm SHA256",
           "Fingerprint a local file for comparison.",
           "-LiteralPath: use the exact path.  -Algorithm: select SHA-256.",
           "Algorithm, digest, and file path.",
           docs="https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash"),
    recipe("ps-events", "PowerShell", "Read recent system errors",
           "Get-WinEvent -FilterHashtable @{LogName='System'; Level=2} -MaxEvents 20",
           "Review recent Windows System log error events.",
           "Level=2: errors.  -MaxEvents 20: limit returned entries.",
           "Up to twenty matching events, newest first.",
           docs="https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent"),
    recipe("ps-dns", "PowerShell", "Resolve a DNS name", "Resolve-DnsName -Name {host} -Type A",
           "Inspect DNS answers using built-in Windows tooling.",
           "-Name: hostname.  -Type A: IPv4 records.",
           "DNS records and their TTLs.",
           docs="https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname"),
    recipe("sys-sigcheck", "Sysinternals", "Inspect signature and hashes",
           "sigcheck64.exe -nobanner -h -i app.exe",
           "Examine a local executable's hashes and signing information.",
           "-h: hashes.  -i: catalog and signing-chain information.",
           "File identity, hashes, and signature details.", "This recipe does not request a VirusTotal submission.",
           "https://learn.microsoft.com/en-us/sysinternals/downloads/sigcheck"),
    recipe("sys-config", "Sysinternals", "View installed Sysmon configuration", "sysmon64.exe -c",
           "Inspect the configuration of an existing Sysmon installation.",
           "-c without a configuration file: display the active configuration.",
           "Current Sysmon configuration.",
           "Sysmon must already be installed; appropriate administrator rights may be required.",
           "https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon"),
    recipe("sys-events", "Sysinternals", "Read recent Sysmon events",
           "Get-WinEvent -LogName 'Microsoft-Windows-Sysmon/Operational' -MaxEvents 20",
           "Read recent events recorded by Sysmon.",
           "-LogName: Sysmon's operational log.  -MaxEvents: bounded result count.",
           "Recent telemetry according to the installed Sysmon configuration.",
           "Run in PowerShell on a system where Sysmon is installed.",
           "https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon"),
    recipe("jq-count", "jq", "Read the CISA catalog count", "jq '.count' kev.json",
           "Read the record count from a downloaded KEV catalog.",
           ".count: access the catalog count field.", "The catalog's declared entry count."),
    recipe("jq-recent", "jq", "List recent KEV additions",
           'jq -r ".vulnerabilities | sort_by(.dateAdded) | reverse | .[:10][] | [.dateAdded, .cveID, .product] | @tsv" kev.json',
           "Create a compact view of recent known-exploited additions.",
           "-r: raw output.  sort_by/reverse: newest first.  @tsv: tab-separated fields.",
           "Ten rows containing date added, CVE, and product.", "Use a current catalog download; dateAdded is not the original disclosure date."),
]
RECIPE_BY_ID = {entry["id"]: entry for entry in RECIPES}


def search_recipes(query="", tool="All tools", favorites=None):
    terms = query.lower().split()
    return [entry for entry in RECIPES
            if (tool == "All tools" or entry["tool"] == tool)
            and (favorites is None or entry["id"] in favorites)
            and all(term in (" ".join(str(value) for value in entry.values()) + " " + TOOLS[entry["tool"]]["category"]).lower()
                    for term in terms)]


def build_command(entry, host="127.0.0.1", ports="22,80,443"):
    command = entry["command"]
    if "{host}" in command:
        host = host.strip()
        if not host or len(host) > 253 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./-]*", host):
            raise ValueError("Use one IPv4 address, hostname, or supported Nmap CIDR range.")
        if "/" in host:
            if entry["tool"] != "Nmap":
                raise ValueError("This command expects a single host, not a CIDR range.")
            try:
                if ipaddress.ip_network(host, strict=False).version != 4:
                    raise ValueError()
            except ValueError:
                raise ValueError("Enter a valid IPv4 CIDR range.") from None
        elif re.fullmatch(r"[0-9.]+", host):
            try:
                ipaddress.IPv4Address(host)
            except ValueError:
                raise ValueError("Enter a valid IPv4 address.") from None
        elif any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", part)
                 for part in host.rstrip(".").split(".")):
            raise ValueError("Enter a valid hostname without a URL scheme.")
        command = command.replace("{host}", host)
    if "{ports}" in command:
        ports = ports.strip()
        if len(ports) > 100 or not re.fullmatch(r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*", ports):
            raise ValueError("Use ports such as 22,80,443 or 8000-8080.")
        for group in ports.split(","):
            bounds = [int(value) for value in group.split("-")]
            if any(not 1 <= value <= 65535 for value in bounds) or (len(bounds) == 2 and bounds[0] > bounds[1]):
                raise ValueError("Ports must be between 1 and 65535, with ranges in ascending order.")
        command = command.replace("{ports}", ports)
    return command


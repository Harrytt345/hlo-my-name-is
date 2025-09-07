import os
import requests
import subprocess
from vars import CREDIT
from pyrogram import Client, filters
from pyrogram.types import Message

#==================================================================================================================================

# Function to extract names and URLs from the text file
def extract_names_and_urls(file_content):
    lines = [line.strip() for line in file_content.strip().split("\n") if line.strip()]
    data = []
    
    i = 0
    while i < len(lines):
        current_line = lines[i]
        
        # Check if current line contains both name and URL (name: url format)
        if ":" in current_line and ("http://" in current_line or "https://" in current_line):
            parts = current_line.split(":", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                url = parts[1].strip()
                data.append((name, url))
            i += 1
            
        # Check if current line is a title and next line is a URL (alternating format)
        elif (i + 1 < len(lines) and 
              not ("http://" in current_line or "https://" in current_line) and 
              ("http://" in lines[i + 1] or "https://" in lines[i + 1])):
            name = current_line.strip()
            url = lines[i + 1].strip()
            data.append((name, url))
            i += 2  # Skip both title and URL lines
            
        else:
            i += 1
    
    return data

#==================================================================================================================================

# Function to categorize URLs
def categorize_urls(urls):
    videos = []
    pdfs = []
    others = []

    for name, url in urls:
        new_url = url
        if "akamaized.net/" in url or "1942403233.rsc.cdn77.org/" in url:
            vid_id = url.split("/")[-2]
            new_url = f"https://www.khanglobalstudies.com/player?src={url}"
            videos.append((name, new_url))

        elif "d1d34p8vz63oiq.cloudfront.net/" in url:
            vid_id = url.split("/")[-2]
            new_url = f"https://anonymouspwplayer-0e5a3f512dec.herokuapp.com/pw?url={url}&token={your_working_token}"
            videos.append((name, new_url))
                    
        elif "youtube.com/embed" in url:
            yt_id = url.split("/")[-1]
            new_url = f"https://www.youtube.com/watch?v={yt_id}"
            
        elif ".m3u8" in url:
            videos.append((name, url))
        elif ".mp4" in url:
            videos.append((name, url))
        elif "pdf" in url:
            pdfs.append((name, url))
        else:
            others.append((name, url))

    return videos, pdfs, others

#=================================================================================================================================

# Function to generate modern HTML file with glass design and Plyr player
def generate_html(file_name, videos, pdfs, others):
    file_name_without_extension = os.path.splitext(file_name)[0]
    
    # Count statistics
    total_videos = len(videos)
    total_pdfs = len(pdfs)
    total_others = len(others)
    total_items = total_videos + total_pdfs + total_others

    # Generate video links with modern styling
    video_links = ""
    for i, (name, url) in enumerate(videos, 1):
        # Clean the name for display and JavaScript safety
        clean_name = name.replace('"', '&quot;').replace("'", "&#39;").replace('\\', '\\\\')
        clean_url = url.replace("'", "\\'").replace('"', '\\"')
        
        video_links += f'''
        <div class="list-group-item" onclick="playVideo('{clean_url}', '{clean_name}')">
            <div class="item-title">
                <i class="fas fa-play-circle"></i>
                <span title="{clean_name}">{name}</span>
            </div>
            <div class="item-actions">
                <small class="text-muted">Video {i:03d}</small>
                <i class="fas fa-play"></i>
            </div>
        </div>'''

    # Generate PDF links with modern styling
    pdf_links = ""
    for i, (name, url) in enumerate(pdfs, 1):
        pdf_links += f'''
        <div class="list-group-item" onclick="window.open('{url}', '_blank')">
            <div class="item-title">
                <i class="fas fa-file-pdf"></i>
                <span>{name}</span>
            </div>
            <div class="item-actions">
                <small class="text-muted">PDF {i:03d}</small>
                <i class="fas fa-external-link-alt ms-2"></i>
            </div>
        </div>'''

    # Generate other links with modern styling
    other_links = ""
    for i, (name, url) in enumerate(others, 1):
        other_links += f'''
        <div class="list-group-item" onclick="window.open('{url}', '_blank')">
            <div class="item-title">
                <i class="fas fa-link"></i>
                <span>{name}</span>
            </div>
            <div class="item-actions">
                <small class="text-muted">Link {i:03d}</small>
                <i class="fas fa-external-link-alt ms-2"></i>
            </div>
        </div>'''

    html_template = f'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>{file_name_without_extension}</title>
    <link href="https://cdn.plyr.io/3.7.8/plyr.css" rel="stylesheet" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    
    <!-- HLS.js for M3U8 support -->
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script src="https://cdn.jsdelivr.net/npm/js-base64@3.7.5/base64.min.js"></script>
    <style>
        /* Modern CSS Variables for Theme Support */
        :root[data-theme="light"] {{
            --bs-body-bg: #f8fafc;
            --bs-body-color: #1e293b;
            --card-bg: rgba(255, 255, 255, 0.9);
            --card-border: rgba(0, 0, 0, 0.1);
            --hover-bg: rgba(59, 130, 246, 0.1);
            --icon-color: #3b82f6;
            --input-color: #1e293b;
            --input-placeholder: #64748b;
            --tab-active: #3b82f6;
            --tab-inactive: #64748b;
            --accent-gradient: linear-gradient(45deg, #3b82f6, #10b981);
        }}
        :root[data-theme="dark"] {{
            --bs-body-bg: #0f172a;
            --bs-body-color: #e2e8f0;
            --card-bg: rgba(255, 255, 255, 0.1);
            --card-border: rgba(255, 255, 255, 0.2);
            --hover-bg: rgba(59, 130, 246, 0.2);
            --icon-color: #60a5fa;
            --input-color: #e2e8f0;
            --input-placeholder: rgba(226, 232, 240, 0.5);
            --tab-active: #ffffff;
            --tab-inactive: #94a3b8;
            --accent-gradient: linear-gradient(45deg, #60a5fa, #34d399);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bs-body-bg);
            color: var(--bs-body-color);
            overflow-x: hidden;
            width: 100%;
            min-height: 100vh;
            -webkit-text-size-adjust: 100%;
            transition: all 0.3s ease;
            line-height: 1.6;
        }}

        .container-fluid {{
            padding-left: max(15px, env(safe-area-inset-left));
            padding-right: max(15px, env(safe-area-inset-right));
        }}

        /* Modern Typography */
        .brand-title {{
            font-size: min(2.5rem, 8vw);
            font-weight: 900;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-align: center;
            width: 100%;
            animation: gradientText 3s ease infinite;
        }}

        .header-title {{
            font-size: min(1.8rem, 6vw);
            font-weight: 700;
            overflow-wrap: break-word;
            word-wrap: break-word;
            hyphens: auto;
            max-width: 100%;
            text-align: center;
            margin-bottom: 2rem;
        }}

        @keyframes gradientText {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}

        /* Glass Card Effects */
        .glass-card {{
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-radius: 16px;
            border: 1px solid var(--card-border);
            transition: all 0.3s ease;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }}

        .glass-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.47);
        }}

        /* Statistics Display */
        .stats-container {{
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}

        .stat-item {{
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--card-border);
            text-align: center;
            min-width: 120px;
            transition: all 0.3s ease;
        }}

        .stat-item:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }}

        .stat-number {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--icon-color);
            margin-bottom: 0.25rem;
            font-variant: small-caps;
        }}

        .stat-label {{
            font-size: 0.875rem;
            color: var(--bs-body-color);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            opacity: 0.8;
        }}

        /* Video Player Container */
        .video-container {{
            position: relative;
            width: 100%;
            max-width: 1000px;
            margin: 0 auto 2rem auto;
            aspect-ratio: 16/9;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }}

        .video-container video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}

        .plyr {{
            width: 100%;
            height: 100%;
            border-radius: 16px;
        }}

        /* Modern Navigation Tabs */
        .nav-tabs {{
            display: flex;
            flex-wrap: nowrap;
            overflow-x: auto;
            scrollbar-width: none;
            -ms-overflow-style: none;
            border: none;
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border-radius: 12px;
            padding: 0.5rem;
            margin-bottom: 1.5rem;
        }}

        .nav-tabs::-webkit-scrollbar {{ display: none; }}

        .nav-tabs .nav-link {{
            background: transparent;
            border: none;
            color: var(--tab-inactive);
            font-weight: 600;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            transition: all 0.3s ease;
            margin: 0 0.25rem;
            white-space: nowrap;
        }}

        .nav-tabs .nav-link.active {{
            background: var(--icon-color);
            color: white;
            transform: translateY(-2px);
        }}

        .nav-tabs .nav-link:hover {{
            color: var(--tab-active);
            background: var(--hover-bg);
        }}

        /* Modern List Items */
        .list-group-item {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            color: var(--bs-body-color);
            transition: all 0.3s ease;
            margin-bottom: 0.75rem;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.25rem;
            cursor: pointer;
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(8px);
        }}

        .list-group-item::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            width: 4px;
            height: 100%;
            background: var(--icon-color);
            opacity: 0;
            transition: all 0.3s ease;
        }}

        .list-group-item:hover {{
            background: var(--hover-bg);
            transform: translateX(8px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }}

        .list-group-item:hover::before {{
            opacity: 1;
        }}

        .item-title {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex: 1;
            font-weight: 500;
        }}

        .item-title i {{
            font-size: 1.2rem;
            color: var(--icon-color);
            width: 20px;
            text-align: center;
        }}

        .item-actions {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            opacity: 0.7;
        }}

        /* Search Input */
        .search-input {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            color: var(--input-color);
            border-radius: 12px;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            width: 100%;
            backdrop-filter: blur(8px);
            transition: all 0.3s ease;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--icon-color);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            background: var(--card-bg);
        }}

        .search-input::placeholder {{
            color: var(--input-placeholder);
        }}

        /* Theme Toggle Button */
        .theme-toggle {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(16px);
            z-index: 1000;
        }}

        .theme-toggle:hover {{
            transform: scale(1.1);
            background: var(--hover-bg);
        }}

        .theme-toggle i {{
            font-size: 1.2rem;
            color: var(--icon-color);
        }}

        /* Responsive Design */
        @media (max-width: 768px) {{
            .stats-container {{
                gap: 1rem;
            }}
            
            .stat-item {{
                min-width: 100px;
                padding: 1rem;
            }}
            
            .stat-number {{
                font-size: 1.5rem;
            }}
            
            .brand-title {{
                font-size: 2rem;
                letter-spacing: 1px;
            }}
            
            .header-title {{
                font-size: 1.5rem;
            }}
            
            .glass-card {{
                padding: 1rem;
            }}
            
            .url-input-wrapper {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .custom-url-input {{
                min-width: 100%;
                padding: 14px 16px;
            }}
            
            .custom-url-btn {{
                width: 100%;
                justify-content: center;
                padding: 14px;
            }}
            
            .list-group-item {{
                padding: 0.75rem 1rem;
                flex-direction: column;
                gap: 0.5rem;
                align-items: flex-start;
            }}
            
            .item-actions {{
                width: 100%;
                justify-content: flex-end;
            }}
        }}

        /* Custom Scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
        }}

        ::-webkit-scrollbar-track {{
            background: transparent;
        }}

        ::-webkit-scrollbar-thumb {{
            background: var(--card-border);
            border-radius: 4px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: var(--icon-color);
        }}

        /* Custom URL Input Styles */
        .url-input-wrapper {{
            display: flex;
            gap: 12px;
            align-items: stretch;
            flex-wrap: wrap;
        }}
        
        .custom-url-input {{
            flex: 1;
            min-width: 300px;
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            color: var(--input-color);
            font-size: 14px;
            transition: all 0.3s ease;
            backdrop-filter: blur(8px);
        }}
        
        .custom-url-input:focus {{
            outline: none;
            border-color: var(--icon-color);
            box-shadow: 0 0 8px rgba(59, 130, 246, 0.2);
        }}
        
        .custom-url-btn {{
            padding: 12px 24px;
            border-radius: 10px;
            background: var(--icon-color);
            color: white;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
            font-weight: 600;
            min-height: 46px;
        }}
        
        .custom-url-btn:hover {{
            opacity: 0.9;
            transform: scale(1.02);
        }}

        /* Utility Classes */
        .text-gradient {{
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .extracted-by {{
            text-align: center;
            margin-top: 3rem;
            padding: 2rem;
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            border: 1px solid var(--card-border);
        }}

        .extracted-by .brand {{
            font-size: 1.5rem;
            font-weight: 800;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
    </style>
</head>
<body>
    <!-- Theme Toggle -->
    <div class="theme-toggle" onclick="toggleTheme()">
        <i class="fas fa-sun" id="theme-icon"></i>
    </div>

    <div class="container-fluid py-4">
        <!-- Header -->
        <div class="text-center mb-4">
            <h1 class="brand-title">TheOne DRM Player</h1>
            <h2 class="header-title">{file_name_without_extension}</h2>
        </div>

        <!-- Statistics -->
        <div class="stats-container">
            <div class="stat-item">
                <div class="stat-number">{total_videos}</div>
                <div class="stat-label">Videos</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_pdfs}</div>
                <div class="stat-label">PDFs</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_others}</div>
                <div class="stat-label">Others</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_items}</div>
                <div class="stat-label">Total</div>
            </div>
        </div>

        <!-- Video Player -->
        <div class="video-container">
            <video id="player" playsinline controls>
                <source src="" type="video/mp4" />
                <source src="" type="application/x-mpegURL" />
            </video>
        </div>

        <!-- Custom URL Input -->
        <div class="glass-card">
            <h4 class="text-gradient mb-3">
                <i class="fas fa-globe me-2"></i>Load Custom Video URL
            </h4>
            <div class="url-input-wrapper">
                <input type="url" class="custom-url-input" id="customUrlInput" placeholder="Enter video URL (mp4, m3u8, etc.)" />
                <button class="custom-url-btn" onclick="loadCustomUrl()">
                    <i class="fas fa-play"></i>
                    Load Video
                </button>
            </div>
        </div>

        <!-- Search Bar -->
        <div class="glass-card">
            <div class="mb-3">
                <input type="text" class="search-input" id="searchInput" placeholder="🔍 Search videos, PDFs, or resources..." oninput="filterContent()">
            </div>
        </div>

        <!-- Navigation Tabs -->
        <ul class="nav nav-tabs" id="contentTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="videos-tab" data-bs-toggle="tab" data-bs-target="#videos" type="button" role="tab">
                    <i class="fas fa-play-circle me-2"></i>Videos ({total_videos})
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="pdfs-tab" data-bs-toggle="tab" data-bs-target="#pdfs" type="button" role="tab">
                    <i class="fas fa-file-pdf me-2"></i>PDFs ({total_pdfs})
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="others-tab" data-bs-toggle="tab" data-bs-target="#others" type="button" role="tab">
                    <i class="fas fa-link me-2"></i>Others ({total_others})
                </button>
            </li>
        </ul>

        <!-- Tab Content -->
        <div class="tab-content" id="contentTabContent">
            <!-- Videos Tab -->
            <div class="tab-pane fade show active" id="videos" role="tabpanel">
                <div class="glass-card">
                    <h3 class="text-gradient mb-3">
                        <i class="fas fa-video me-2"></i>Video Lectures
                    </h3>
                    <div class="list-group list-group-flush">
                        {video_links if video_links else '<div class="text-center text-muted p-4"><i class="fas fa-video fa-2x mb-2 d-block"></i>No videos found</div>'}
                    </div>
                </div>
            </div>

            <!-- PDFs Tab -->
            <div class="tab-pane fade" id="pdfs" role="tabpanel">
                <div class="glass-card">
                    <h3 class="text-gradient mb-3">
                        <i class="fas fa-file-pdf me-2"></i>PDF Documents
                    </h3>
                    <div class="list-group list-group-flush">
                        {pdf_links if pdf_links else '<div class="text-center text-muted p-4"><i class="fas fa-file-pdf fa-2x mb-2 d-block"></i>No PDFs found</div>'}
                    </div>
                </div>
            </div>

            <!-- Others Tab -->
            <div class="tab-pane fade" id="others" role="tabpanel">
                <div class="glass-card">
                    <h3 class="text-gradient mb-3">
                        <i class="fas fa-link me-2"></i>Other Resources
                    </h3>
                    <div class="list-group list-group-flush">
                        {other_links if other_links else '<div class="text-center text-muted p-4"><i class="fas fa-link fa-2x mb-2 d-block"></i>No other resources found</div>'}
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="extracted-by">
            <div class="brand mb-2">Extracted By: {CREDIT}</div>
            <p class="mb-0 text-muted">Professional DRM Content Player • Modern Design • Responsive Layout</p>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
    <script>
        // Initialize video element and player
        const video = document.getElementById('player');
        let hls;
        
        // Initialize Plyr player with enhanced configuration
        const player = new Plyr('#player', {{
            captions: {{ active: true, language: 'auto', update: true }},
            fullscreen: {{ iosNative: true, fallback: true, enabled: true }},
            controls: [
                'play-large', 'restart', 'rewind', 'play', 'fast-forward', 
                'progress', 'current-time', 'duration', 'mute', 'volume', 
                'captions', 'settings', 'pip', 'airplay', 'fullscreen'
            ],
            settings: ['captions', 'quality', 'speed', 'loop'],
            quality: {{ default: 720, options: [4320, 2880, 2160, 1440, 1080, 720, 576, 480, 360, 240] }},
            speed: {{ selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 3, 4] }},
            tooltips: {{ controls: true, seek: true }},
            keyboard: {{ focused: true, global: true }},
            resetOnEnd: true
        }});

        // Load custom URL function
        function loadCustomUrl() {{
            const urlInput = document.getElementById('customUrlInput');
            const url = urlInput.value.trim();
            
            if (!url) {{
                showNotification('Please enter a valid video URL', 'warning');
                return;
            }}
            
            // Validate URL format
            try {{
                new URL(url);
            }} catch {{
                showNotification('Please enter a valid URL format', 'error');
                return;
            }}
            
            playVideo(url, 'Custom Video');
            urlInput.value = ''; // Clear input after loading
        }}
        
        // Add Enter key support for custom URL input
        document.addEventListener('DOMContentLoaded', function() {{
            const customUrlInput = document.getElementById('customUrlInput');
            if (customUrlInput) {{
                customUrlInput.addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') {{
                        loadCustomUrl();
                    }}
                }});
            }}
        }});

        // Enhanced play video function with better debugging
        function playVideo(url, title = '') {{
            console.log('playVideo called with:', url, title);
            
            if (!url || url === 'undefined') {{
                showNotification('Invalid video URL', 'error');
                return;
            }}
            
            if (url.includes('utkarshapp.com')) {{
                window.open(url, '_blank');
                return;
            }}
            
            // Load the video
            loadVideo(url, title);
            
            // Scroll to player smoothly
            setTimeout(() => {{
                document.querySelector('.video-container').scrollIntoView({{ 
                    behavior: 'smooth',
                    block: 'center'
                }});
            }}, 100);
        }}
        
        // Enhanced load video function with better HLS.js support and debugging
        function loadVideo(url, title = '') {{
            let videoTitle = title || 'Video Player';
            
            console.log('loadVideo called with URL:', url);
            console.log('Video title:', videoTitle);
            
            // Update page title and show in console
            if (title) {{
                document.title = `${{title}} - Enhanced Player`;
            }}
            
            // Clean up previous HLS instance
            if (hls) {{
                hls.destroy();
                hls = null;
                console.log('Previous HLS instance destroyed');
            }}
            
            // Reset video element
            video.pause();
            video.removeAttribute('src');
            video.load();
            
            // Show loading notification
            showNotification(`Loading: ${{videoTitle}}`, 'info');
            
            // Handle M3U8/HLS streams
            if (url.includes('.m3u8') || url.includes('m3u8')) {{
                console.log('Detected M3U8 stream, using HLS.js');
                
                if (Hls.isSupported()) {{
                    hls = new Hls({{
                        enableWorker: true,
                        lowLatencyMode: false,
                        backBufferLength: 90,
                        maxLoadingDelay: 4,
                        maxMaxBufferLength: 30
                    }});
                    
                    hls.loadSource(url);
                    hls.attachMedia(video);
                    
                    hls.on(Hls.Events.MANIFEST_PARSED, function(event, data) {{
                        console.log('HLS manifest parsed successfully', data);
                        showNotification(`Ready: ${{videoTitle}}`, 'success');
                        
                        // Try to auto-play
                        setTimeout(() => {{
                            player.play().catch(e => {{
                                console.log('Auto-play prevented by browser:', e);
                                showNotification('Video ready - Click play button', 'warning');
                            }});
                        }}, 1500);
                    }});
                    
                    hls.on(Hls.Events.ERROR, function(event, data) {{
                        console.error('HLS error:', event, data);
                        if (data.fatal) {{
                            switch(data.type) {{
                                case Hls.ErrorTypes.NETWORK_ERROR:
                                    console.log('Fatal network error encountered, trying to recover');
                                    hls.startLoad();
                                    break;
                                case Hls.ErrorTypes.MEDIA_ERROR:
                                    console.log('Fatal media error encountered, trying to recover');
                                    hls.recoverMediaError();
                                    break;
                                default:
                                    console.log('Fatal error, cannot recover');
                                    showNotification('Error loading video stream', 'error');
                                    break;
                            }}
                        }}
                    }});
                    
                }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
                    console.log('Using native HLS support (Safari)');
                    video.src = url;
                    video.load();
                    showNotification(`Ready: ${{videoTitle}}`, 'success');
                    
                    video.addEventListener('loadeddata', function() {{
                        console.log('Native HLS video loaded');
                        player.play().catch(e => {{
                            console.log('Auto-play prevented:', e);
                            showNotification('Video ready - Click play button', 'warning');
                        }});
                    }});
                    
                }} else {{
                    console.log('HLS not supported in this browser');
                    showNotification('HLS video format not supported in this browser', 'error');
                }}
                
            }} else {{
                console.log('Detected MP4 or other format');
                // Handle MP4 and other formats
                video.src = url;
                video.load();
                
                video.addEventListener('loadeddata', function() {{
                    console.log('MP4 video loaded successfully');
                    showNotification(`Ready: ${{videoTitle}}`, 'success');
                    
                    // Auto-play for MP4
                    setTimeout(() => {{
                        player.play().catch(e => {{
                            console.log('Auto-play prevented:', e);
                            showNotification('Video ready - Click play button', 'warning');
                        }});
                    }}, 500);
                }});
                
                video.addEventListener('error', function(e) {{
                    console.error('Video load error:', e);
                    showNotification('Error loading video file', 'error');
                }});
            }}
        }}
        
        // Enhanced notification system
        function showNotification(message, type = 'info') {{
            const notification = document.createElement('div');
            notification.className = `notification notification-${{type}}`;
            
            // Define colors for different types
            let bgColor = 'var(--card-bg)';
            let borderColor = 'var(--card-border)';
            let textColor = 'var(--bs-body-color)';
            
            if (type === 'success') {{
                bgColor = 'rgba(16, 185, 129, 0.2)';
                borderColor = '#10b981';
                textColor = '#10b981';
            }} else if (type === 'error') {{
                bgColor = 'rgba(239, 68, 68, 0.2)';
                borderColor = '#ef4444';
                textColor = '#ef4444';
            }} else if (type === 'warning') {{
                bgColor = 'rgba(245, 158, 11, 0.2)';
                borderColor = '#f59e0b';
                textColor = '#f59e0b';
            }}
            
            notification.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                background: ${{bgColor}};
                color: ${{textColor}};
                padding: 16px 24px;
                border-radius: 12px;
                border: 2px solid ${{borderColor}};
                backdrop-filter: blur(16px);
                z-index: 9999;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                transform: translateX(120%);
                transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                font-weight: 600;
                font-size: 14px;
                max-width: 300px;
                word-wrap: break-word;
            `;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            // Animate in
            setTimeout(() => {{
                notification.style.transform = 'translateX(0)';
            }}, 100);
            
            // Remove after duration based on type
            const duration = type === 'error' ? 5000 : 3000;
            setTimeout(() => {{
                notification.style.transform = 'translateX(120%)';
                setTimeout(() => {{
                    if (notification.parentNode) {{
                        notification.remove();
                    }}
                }}, 400);
            }}, duration);
        }}

        // Theme management
        function toggleTheme() {{
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            const icon = document.getElementById('theme-icon');
            
            html.setAttribute('data-theme', newTheme);
            icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            
            localStorage.setItem('theme', newTheme);
        }}

        // Load saved theme
        function loadTheme() {{
            const savedTheme = localStorage.getItem('theme') || 'dark';
            const icon = document.getElementById('theme-icon');
            
            document.documentElement.setAttribute('data-theme', savedTheme);
            icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }}

        // Filter content based on search
        function filterContent() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const allItems = document.querySelectorAll('.list-group-item');
            let visibleCount = 0;

            allItems.forEach(item => {{
                const text = item.textContent.toLowerCase();
                if (text.includes(searchTerm)) {{
                    item.style.display = 'flex';
                    visibleCount++;
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }}

        // Initialize on load
        document.addEventListener('DOMContentLoaded', function() {{
            loadTheme();
            
            // Auto-play first video if available
            const firstVideo = document.querySelector('.list-group-item[onclick*="playVideo"]');
            if (firstVideo) {{
                const url = firstVideo.getAttribute('onclick').match(/'([^']+)'/)[1];
                setTimeout(() => playVideo(url), 1000);
            }}
        }});

        // Enhanced search with keyboard shortcuts
        document.getElementById('searchInput').addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                this.value = '';
                filterContent();
                this.blur();
            }}
        }});

        // Progressive Web App features
        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', function() {{
                navigator.serviceWorker.register('/sw.js').then(function(registration) {{
                    console.log('SW registered: ', registration);
                }}, function(registrationError) {{
                    console.log('SW registration failed: ', registrationError);
                }});
            }});
        }}
    </script>
</body>
</html>'''
    return html_template

# Function to download video using FFmpeg
def download_video(url, output_path):
    command = f"ffmpeg -i {url} -c copy {output_path}"
    subprocess.run(command, shell=True, check=True)




#======================================================================================================================================================================================

async def html_handler(bot: Client, message: Message):
    editable = await message.reply_text("𝐖𝐞𝐥𝐜𝐨𝐦𝐞! 𝐏𝐥𝐞𝐚𝐬𝐞 𝐮𝐩𝐥𝐨𝐚𝐝 𝐚 .𝐭𝐱𝐭 𝐟𝐢𝐥𝐞 𝐜𝐨𝐧𝐭𝐚𝐢𝐧𝐢𝐧𝐠 𝐔𝐑𝐋𝐬.✓")
    input: Message = await bot.listen(editable.chat.id)
    if input.document and input.document.file_name.endswith('.txt'):
        file_path = await input.download()
        file_name, ext = os.path.splitext(os.path.basename(file_path))
        b_name = file_name.replace('_', ' ')
    else:
        await message.reply_text("**• Invalid file input.**")
        return
           
    with open(file_path, "r") as f:
        file_content = f.read()

    urls = extract_names_and_urls(file_content)

    videos, pdfs, others = categorize_urls(urls)

    html_content = generate_html(file_name, videos, pdfs, others)
    html_file_path = file_path.replace(".txt", ".html")
    with open(html_file_path, "w") as f:
        f.write(html_content)

    await message.reply_document(document=html_file_path, caption=f"✅𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 𝐃𝐨𝐧𝐞!\n<blockquote><b>`{b_name}`</b></blockquote>\n❖**Open in Chrome.**\n\n🌟**Extracted By : {CREDIT}**")
    os.remove(file_path)
    os.remove(html_file_path)
    

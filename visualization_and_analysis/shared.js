let allData = {};
let allModels = [];
const selectedCategories = [];
let selectedModels = new Set();
let queryModelData = {};

function initializeModelView() {
    setupModelSelector();
    loadAllJSON();
}

function setupModelSelector() {
    const searchBox = document.getElementById('modelSearch');
    
    searchBox.addEventListener('input', () => {
        const searchTerm = searchBox.value.toLowerCase();
        renderModelGrid(searchTerm);
    });
}

function renderModelGrid(searchTerm = '') {
    const modelGrid = document.getElementById('modelGrid');
    modelGrid.innerHTML = '';
    
    // Sort by Score
    const sortedModels = [...allModels].sort((a, b) => {
        // Get score values for each model
        const scoreA = allData[a]?.score || 0;
        const scoreB = allData[b]?.score || 0;
        // Sort by score in descending order
        return scoreB - scoreA;
    });
    
    const modelsToShow = searchTerm 
        ? sortedModels.filter(model => model.toLowerCase().includes(searchTerm.toLowerCase()))
        : sortedModels;
    
    modelsToShow.forEach(model => {
        const modelItem = document.createElement('div');
        modelItem.className = 'model-item';
        if (selectedModels.has(model)) {
            modelItem.classList.add('selected');
        }
        modelItem.textContent = model;
        modelItem.title = model;
        
        modelItem.addEventListener('click', () => {
            if (selectedModels.has(model)) {
                selectedModels.delete(model);
                modelItem.classList.remove('selected');
                
                // Remove from selected categories
                const idx = selectedCategories.indexOf(model);
                if (idx > -1) {
                    selectedCategories.splice(idx, 1);
                }
            } else {
                selectedModels.add(model);
                modelItem.classList.add('selected');
                
                // Add to selected categories
                if (!selectedCategories.includes(model)) {
                    selectedCategories.push(model);
                }
            }
            
            renderSelectedTrees();
        });
        
        modelGrid.appendChild(modelItem);
    });
}

// GitHub API 处理函数
async function fetchFromGitHub(url, token = null) {
  // 创建请求头
  const headers = {
    'Accept': 'application/vnd.github.v3+json'
  };

  // 如果提供了令牌，添加到请求头中
  if (token) {
    headers['Authorization'] = `token ${token}`;
  }

  // 添加延迟和重试逻辑
  let retries = 3;
  let delay = 1000; // 初始延迟1秒

  while (retries > 0) {
    try {
      const response = await fetch(url, { headers });

      // 检查是否接近速率限制
      const rateLimit = response.headers.get('X-RateLimit-Remaining');
      if (rateLimit && parseInt(rateLimit) < 10) {
        console.warn(`GitHub API rate limit running low: ${rateLimit} requests remaining`);
      }

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`GitHub API error: ${response.status} 和 ${JSON.stringify(errorData)}`);
      }
    } catch (error) {
      retries--;
      if (error.message.includes('403') && error.message.includes('rate limit exceeded')) {
        // 如果是速率限制错误，等待更长时间
        console.warn(`Rate limit exceeded, waiting before retry. Retries left: ${retries}`);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= 2; // 指数退避
      } else if (retries <= 0) {
        throw error;
      } else {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
}

// 统一的数据加载函数
async function loadJsonFiles() {
  // 检查是否在 GitHub Pages 上运行
  const isGitHubPages = window.location.hostname.includes('github.io') ||
                        window.location.hostname.includes('liudan193.github.io');

  // 可以从本地存储或配置中获取 GitHub token
  const githubToken = localStorage.getItem('github_token') || null;

  try {
    let filesData = [];

    if (isGitHubPages) {
      // GitHub Pages 实现
      const owner = 'liudan193';
      const repo = 'Feedbacker';
      const path = 'visualization_and_analysis/processed_data';

      // 使用我们的函数获取目录列表
      const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
      const files = await fetchFromGitHub(apiUrl, githubToken);

      // 筛选 JSON 文件
      const jsonFiles = files.filter(file => file.name.endsWith('.json'));

      // 使用缓存逻辑
      const cachedData = {};
      const cacheKey = `github_files_cache_${owner}_${repo}_${path}`;
      const cacheExpiry = `github_files_cache_expiry_${owner}_${repo}_${path}`;

      // 检查缓存
      try {
        const cachedStr = localStorage.getItem(cacheKey);
        const expiryTime = localStorage.getItem(cacheExpiry);

        if (cachedStr && expiryTime && Date.now() < parseInt(expiryTime)) {
          console.log("Using cached GitHub data");
          return JSON.parse(cachedStr);
        }
      } catch (e) {
        console.warn("Cache error:", e);
      }

      // 获取所有文件内容
      filesData = await Promise.all(
        jsonFiles.map(async file => {
          try {
            // 使用下载链接获取文件内容
            const data = await fetchFromGitHub(file.download_url, githubToken);
            return { name: file.name.replace(/\.json$/i, ''), data };
          } catch (err) {
            console.error(`Error loading ${file.name}:`, err);
            return null;
          }
        })
      );

      // 更新缓存
      try {
        // 过滤掉空值
        const validFiles = filesData.filter(item => item !== null);
        localStorage.setItem(cacheKey, JSON.stringify(validFiles));
        // 设置 12 小时的缓存过期时间
        localStorage.setItem(cacheExpiry, (Date.now() + 12 * 60 * 60 * 1000).toString());
      } catch (e) {
        console.warn("Failed to cache data:", e);
      }

    } else {
      // 本地实现
      const listResponse = await fetch('processed_data/');
      const listText = await listResponse.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(listText, 'text/html');

      // 获取所有可能是 JSON 文件的链接
      const links = Array.from(doc.querySelectorAll('a'))
          .map(a => a.getAttribute('href'))
          .filter(href => href && typeof href === 'string' && href.toLowerCase().endsWith('.json'));

      // 加载每个 JSON 文件
      filesData = await Promise.all(links.map(async file => {
        try {
          const resp = await fetch(`processed_data/${file}`);
          const data = await resp.json();
          return { name: file.replace(/\.json$/i, ''), data };
        } catch (err) {
          console.error(`Error loading ${file}:`, err);
          return null;
        }
      }));
    }

    // 过滤掉无效数据
    return filesData.filter(item => item !== null);

  } catch (error) {
    console.error("Failed to load data:", error);
    throw error;
  }
}

// 更新后的 loadAllJSON 函数
async function loadAllJSON() {
  try {
    // 使用统一的加载函数
    const filesData = await loadJsonFiles();

    // 填充全局数据结构
    filesData.forEach(({ name, data }) => {
      allData[name] = data;
    });
    allModels = Object.keys(allData);

    // 隐藏加载指示器，显示查看器
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('viewer').classList.remove('hidden');

    // 初始渲染模型网格
    renderModelGrid();

    // 默认选择按得分排序的前 4 个模型
    const sorted = [...allModels].sort((a, b) => {
      const sa = allData[a]?.score || 0;
      const sb = allData[b]?.score || 0;
      return sb - sa;
    });
    const topModels = sorted.slice(0, 4);
    topModels.forEach(model => {
      selectedModels.add(model);
      if (!selectedCategories.includes(model)) {
        selectedCategories.push(model);
      }
    });

    // 重新渲染选择
    renderModelGrid();
    renderSelectedTrees();

  } catch (error) {
    document.getElementById('loading').classList.add('hidden');
    const errEl = document.getElementById('error');
    errEl.classList.remove('hidden');
    errEl.textContent = `Error: ${error.message}`;
  }
}

// 更新后的 loadAllQueryModelData 函数
async function loadAllQueryModelData() {
  try {
    // 使用统一的加载函数
    const filesData = await loadJsonFiles();

    // 填充 queryModelData 全局数据结构
    filesData.forEach(({ name, data }) => {
      queryModelData[name] = data;
    });

    console.log(`Loaded ${Object.keys(queryModelData).length} model files`);
    return queryModelData;

  } catch (error) {
    console.error("Failed to load model data:", error);
    throw error;
  }
}

// 辅助函数：设置 GitHub 个人访问令牌
function setGitHubToken(token) {
  if (token && token.trim() !== '') {
    localStorage.setItem('github_token', token.trim());
    return true;
  } else {
    localStorage.removeItem('github_token');
    return false;
  }
}

// 添加一个设置页面或弹窗来让用户输入他们的令牌
function showTokenInputDialog() {
  const instructions = `
要获取 GitHub 个人访问令牌，请按照以下步骤操作：

1. 登录您的 GitHub 账户
2. 点击右上角头像 → Settings (设置)
3. 滚动到底部，点击左侧菜单的 Developer settings (开发者设置)
4. 点击左侧菜单的 Personal access tokens (个人访问令牌)
5. 点击 Generate new token (生成新令牌) → Fine-grained tokens
6. 输入令牌描述，如 "Feedbacker App"
7. 设置过期时间，推荐选择 90 天
8. 在 Repository access 中选择 "Only select repositories" 并选择 "liudan193/Feedbacker"
9. Permission 部分仅需选择 "Contents" 的 "Read-only" 权限
10. 点击底部的 Generate token (生成令牌)
11. 复制显示的令牌值 (注意: 您只能看到一次!)

请复制生成的令牌，并粘贴到下方:
`;

  const token = prompt(instructions);

  if (token) {
    const success = setGitHubToken(token);
    if (success) {
      alert("令牌已成功保存！您现在可以刷新页面重试。");
    } else {
      alert("令牌格式可能有误，请确保完整复制了整个令牌。");
      // 重新尝试
      setTimeout(showTokenInputDialog, 500);
    }
  }
}

// 可以添加一个错误处理器来检测特定错误并显示提示
window.addEventListener('error', function(event) {
  if (event.error && event.error.message &&
      event.error.message.includes('GitHub API') &&
      event.error.message.includes('403')) {
    // 提示用户设置令牌
    if (confirm("检测到 GitHub API 速率限制错误。是否要设置个人访问令牌来增加限制？")) {
      showTokenInputDialog();
    }
  }
});

// async function loadAllJSON() {
//   try {
//     // Check if we're running on GitHub Pages or locally
//     const isGitHubPages = window.location.hostname.includes('github.io') ||
//                          window.location.hostname.includes('liudan193.github.io');
//
//     let filesData;
//
//     if (isGitHubPages) {
//       // GitHub Pages implementation
//       const owner = 'liudan193';
//       const repo = 'Feedbacker';
//       const path = 'visualization_and_analysis/processed_data';
//
//       // Fetch directory listing via GitHub API
//       const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
//       const response = await fetch(apiUrl);
//       if (!response.ok) throw new Error(`GitHub API error: ${response.status}`);
//       const files = await response.json();
//
//       // Filter JSON files and fetch their contents
//       const jsonFiles = files.filter(file => file.name.endsWith('.json'));
//       filesData = await Promise.all(
//         jsonFiles.map(async file => {
//           const resp = await fetch(file.download_url);
//           if (!resp.ok) throw new Error(`Failed to load ${file.name}`);
//           const data = await resp.json();
//           return { name: file.name.replace(/\.json$/i, ''), data };
//         })
//       );
//     } else {
//       // Local implementation
//       const listResponse = await fetch('processed_data/');
//       const listText = await listResponse.text();
//       const parser = new DOMParser();
//       const doc = parser.parseFromString(listText, 'text/html');
//       const links = Array.from(doc.querySelectorAll('a'))
//           .map(a => a.getAttribute('href'))
//           .filter(href => href && href.endsWith('.json'));
//
//       filesData = await Promise.all(links.map(async file => {
//           const resp = await fetch(`processed_data/${file}`);
//           const data = await resp.json();
//           return { name: file.replace(/\.json$/i, ''), data };
//       }));
//     }
//
//     // Populate global data structures (same for both implementations)
//     filesData.forEach(({ name, data }) => {
//       allData[name] = data;
//     });
//     allModels = Object.keys(allData);
//
//     // Hide loading indicator, show viewer
//     document.getElementById('loading').classList.add('hidden');
//     document.getElementById('viewer').classList.remove('hidden');
//
//     // Initial render of model grid
//     renderModelGrid();
//
//     // Default-select top 4 models by score
//     const sorted = [...allModels].sort((a, b) => {
//       const sa = allData[a]?.score || 0;
//       const sb = allData[b]?.score || 0;
//       return sb - sa;
//     });
//     const topModels = sorted.slice(0, 4);
//     topModels.forEach(model => {
//       selectedModels.add(model);
//       if (!selectedCategories.includes(model)) {
//         selectedCategories.push(model);
//       }
//     });
//
//     // Re-render with selections
//     renderModelGrid();
//     renderSelectedTrees();
//
//   } catch (error) {
//     document.getElementById('loading').classList.add('hidden');
//     const errEl = document.getElementById('error');
//     errEl.classList.remove('hidden');
//     errEl.textContent = `Error: ${error.message}`;
//   }
// }
//
// async function loadAllQueryModelData() {
//     try {
//         // Check if we're running on GitHub Pages or locally
//         const isGitHubPages = window.location.hostname.includes('github.io') ||
//                              window.location.hostname.includes('liudan193.github.io');
//
//         let filesData;
//
//         if (isGitHubPages) {
//             // GitHub Pages implementation
//             const owner = 'liudan193';
//             const repo = 'Feedbacker';
//             const path = 'visualization_and_analysis/processed_data';
//
//             // Fetch directory listing via GitHub API
//             const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
//             const response = await fetch(apiUrl);
//             if (!response.ok) throw new Error(`GitHub API error: ${response.status}`);
//             const files = await response.json();
//
//             // Filter JSON files
//             const jsonFiles = files.filter(file => file.name.endsWith('.json'));
//
//             // Load each JSON file
//             filesData = await Promise.all(jsonFiles.map(async file => {
//                 try {
//                     const resp = await fetch(file.download_url);
//                     if (!resp.ok) throw new Error(`Failed to load ${file.name}`);
//                     const data = await resp.json();
//                     return { name: file.name.replace(/\.json$/i, ''), data };
//                 } catch (err) {
//                     console.error(`Error loading ${file.name}:`, err);
//                     return null;
//                 }
//             }));
//         } else {
//             // Local implementation
//             const listResponse = await fetch('processed_data/');
//             const listText = await listResponse.text();
//             const parser = new DOMParser();
//             const doc = parser.parseFromString(listText, 'text/html');
//
//             // Get all links that might be JSON files
//             const links = Array.from(doc.querySelectorAll('a'))
//                 .map(a => a.getAttribute('href'))
//                 .filter(href => href && typeof href === 'string' && href.toLowerCase().endsWith('.json'));
//
//             // Load each JSON file
//             filesData = await Promise.all(links.map(async file => {
//                 try {
//                     const resp = await fetch(`processed_data/${file}`);
//                     const data = await resp.json();
//                     return { name: file.replace(/\.json$/i, ''), data };
//                 } catch (err) {
//                     console.error(`Error loading ${file}:`, err);
//                     return null;
//                 }
//             }));
//         }
//
//         // Add valid data to queryModelData (same for both implementations)
//         filesData.forEach(item => {
//             if (item) {
//                 queryModelData[item.name] = item.data;
//             }
//         });
//
//         console.log(`Loaded ${Object.keys(queryModelData).length} model files`);
//         return queryModelData;
//     } catch (error) {
//         console.error("Failed to load model data:", error);
//         throw error;
//     }
// }

function renderSelectedTrees() {
    const container = document.getElementById('treesContainer');
    container.innerHTML = '';

    selectedCategories.forEach(name => {
        const wrapper = document.createElement('div');
        wrapper.className = 'tree-wrapper';
        wrapper.dataset.name = name;

        const header = document.createElement('div');
        header.className = 'tree-header';

        const title = document.createElement('h2');
        title.textContent = name;
        header.appendChild(title);

        const removeBtn = document.createElement('div');
        removeBtn.className = 'remove-btn';
        removeBtn.textContent = '×';
        removeBtn.title = 'Remove this model';
        removeBtn.addEventListener('click', () => {
            selectedModels.delete(name);
            const idx = selectedCategories.indexOf(name);
            if (idx > -1) {
                selectedCategories.splice(idx, 1);
            }
            renderSelectedTrees();
            renderModelGrid();
        });

        const treeCont = document.createElement('div');
        treeCont.className = 'tree-container';
        treeCont.dataset.modelName = name;
        treeCont.appendChild(createBlockNode(name, allData[name], 0, true));

        // Add scroll event listener
        treeCont.addEventListener('scroll', synchronizeScroll);

        wrapper.appendChild(removeBtn);
        wrapper.appendChild(header);
        wrapper.appendChild(treeCont);
        container.appendChild(wrapper);
    });
}

let isScrolling = false;
function synchronizeScroll(event) {
    if (isScrolling) return;

    isScrolling = true;
    const sourceElement = event.target;
    const scrollTop = sourceElement.scrollTop;
    const sourceName = sourceElement.dataset.modelName;

    document.querySelectorAll('.tree-container').forEach(container => {
        if (container.dataset.modelName !== sourceName) {
            container.scrollTop = scrollTop;
        }
    });

    // Allow scrolling again after a short delay
    setTimeout(() => {
        isScrolling = false;
    }, 10);
}

const skipKeys = ['ques_ids', 'ranking'];

function createBlockNode(name, data, depth, isRoot = false) {
    const size = Number.isInteger(data.data_size) ? data.data_size : (data.data_size ? Math.round(data.data_size) : 0);
    const score = typeof data.score === 'number' ? data.score : 0;
    const keys = Object.keys(data).filter(k => !skipKeys.includes(k) && k !== 'data_size' && k !== 'score');

    const nodeDiv = document.createElement('div');
    nodeDiv.className = `node depth-${depth % 6} ${isRoot ? 'root-node' : ''}`;
    if (!keys.length) nodeDiv.classList.add('leaf-node');

    const blockDiv = document.createElement('div');
    blockDiv.className = 'node-block';
    blockDiv.dataset.name = name;

    const left = document.createElement('div');
    left.className = 'node-left';
    const nameEl = document.createElement('div');
    nameEl.className = 'node-name';
    nameEl.textContent = name;
    left.appendChild(nameEl);
    blockDiv.appendChild(left);

    const right = document.createElement('div');
    right.className = 'node-right';
    const info = document.createElement('div');
    info.className = 'node-info';
    const sizeEl = document.createElement('div');
    sizeEl.className = 'node-size';
    sizeEl.textContent = `Size: ${size}`;
    const scoreEl = document.createElement('div');
    scoreEl.className = 'node-score';
    scoreEl.textContent = `Score: ${score.toFixed(2)}`;
    info.appendChild(sizeEl);
    info.appendChild(scoreEl);
    right.appendChild(info);

    if (keys.length) {
        const toggle = document.createElement('div');
        toggle.className = 'toggle-btn';
        toggle.textContent = isRoot ? '-' : '+';
        toggle.addEventListener('click', e => {
            e.stopPropagation();
            const newState = !blockDiv.classList.contains('expanded');
            document.querySelectorAll(`.node-block[data-name="${name}"]`).forEach(b => {
                if (newState) b.classList.add('expanded');
                else b.classList.remove('expanded');
                const t = b.parentNode.querySelector('.toggle-btn');
                if (t) t.textContent = newState ? '-' : '+';
            });
        });
        right.appendChild(toggle);
    }
    blockDiv.appendChild(right);
    nodeDiv.appendChild(blockDiv);

    if (keys.length) {
        const childrenDiv = document.createElement('div');
        childrenDiv.className = 'node-children';
        keys.forEach(key => childrenDiv.appendChild(createBlockNode(key, data[key], depth + 1)));
        nodeDiv.appendChild(childrenDiv);
        if (isRoot) blockDiv.classList.add('expanded');
    }
    return nodeDiv;
}


// shared.js 新增代码
let selectedNodes = new Set();

function initializeQueryView() {
    selectedNodes.clear();
    loadCategoryTree();
}

function loadCategoryTree() {
    fetch('cata_tree.json')
        .then(response => response.json())
        .then(data => buildCategoryTree(data))
        .catch(handleTreeError);
}

function buildCategoryTree(treeData) {
    const container = document.getElementById('categoryTree');
    container.innerHTML = '';
    const rootNode = createTreeNode(treeData, [], container);
    container.appendChild(rootNode);
}

function createTreeNode(nodeData, currentPath, parentElement) {
    const node = document.createElement('div');
    node.className = 'tree-node';
    
    // 节点头部
    const nodeHeader = document.createElement('div');
    nodeHeader.className = 'tree-node-header';
    nodeHeader.textContent = nodeData.name;
    
    // 路径处理
    const path = [...currentPath, nodeData.key].join('.');
    
    // 点击事件
    nodeHeader.addEventListener('click', (e) => {
        e.stopPropagation();
        nodeHeader.classList.toggle('selected');
        updateSelection(path, nodeHeader.classList.contains('selected'));
        renderRankings();
    });

    node.appendChild(nodeHeader);

    // 递归子节点
    if (nodeData.children) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = 'tree-node-children';
        nodeData.children.forEach(child => {
            childrenContainer.appendChild(createTreeNode(child, [...currentPath, nodeData.key], node));
        });
        node.appendChild(childrenContainer);
    }

    return node;
}

function updateSelection(path, isSelected) {
    isSelected ? selectedNodes.add(path) : selectedNodes.delete(path);
}

function renderRankings() {
    const container = document.getElementById('rankingsTable');
    container.innerHTML = '';
    
    Array.from(selectedNodes).forEach(path => {
        // 创建列容器
        const column = document.createElement('div');
        column.className = 'ranking-column';
        
        // 列标题
        const header = document.createElement('div');
        header.className = 'ranking-header';
        header.textContent = path.split('.').pop();
        column.appendChild(header);

        // 获取并排序数据
        const rankings = allModels.map(model => ({
            model,
            ranking: getNestedValue(allData[model], path)?.ranking || Infinity
        })).sort((a, b) => a.ranking - b.ranking);

        // 填充排名数据
        const list = document.createElement('div');
        list.className = 'ranking-list';
        rankings.forEach((item, index) => {
            const entry = document.createElement('div');
            entry.className = 'ranking-entry';
            entry.innerHTML = `
                <div class="rank">${index + 1}.</div>
                <div class="model-name">${item.model}</div>
                <div class="ranking-value">${Number.isFinite(item.ranking) ? item.ranking : 'N/A'}</div>
            `;
            list.appendChild(entry);
        });
        
        column.appendChild(list);
        container.appendChild(column);
    });
}

function getNestedValue(obj, path) {
    return path.split('.').reduce((acc, key) => acc?.[key], obj);
}

function handleTreeError(error) {
    const container = document.getElementById('rankingsTable');
    container.innerHTML = `<div class="error">Error loading category tree: ${error.message}</div>`;
}
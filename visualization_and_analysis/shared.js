let allData = {};
let allModels = [];
const selectedCategories = [];
let selectedModels = new Set();
let queryModelData = {};

// GitHub token management
let githubToken = '';

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

// Global variables
const allData = {};
const queryModelData = {};
let allModels = [];
const selectedModels = new Set();
const selectedCategories = [];

// GitHub token management
let githubToken = '';

/**
 * Load JSON data from either GitHub Pages or local directory
 * @param {string} options.dataPath - The path to the data files
 * @param {object} options.targetObject - The object to populate with data
 * @param {function} options.onSuccess - Callback after successful loading
 * @param {function} options.onError - Callback for error handling
 */
async function loadJSONData({
  dataPath = 'processed_data',
  targetObject = {},
  onSuccess = () => {},
  onError = (error) => { console.error("Data loading error:", error); }
}) {
  try {
    // Check if we're running on GitHub Pages or locally
    const isGitHubPages = window.location.hostname.includes('github.io') ||
                         window.location.hostname.includes('liudan193.github.io');

    let filesData;

    if (isGitHubPages) {
      // GitHub Pages implementation
      const owner = 'liudan193';
      const repo = 'Feedbacker';
      const path = dataPath;

      // Fetch directory listing via GitHub API
      const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;

      // Set up headers (include token if available)
      const headers = {};
      if (githubToken) {
        headers['Authorization'] = `token ${githubToken}`;
      }

      const response = await fetch(apiUrl, { headers });

      if (!response.ok) {
        throw new Error(`GitHub API error: ${response.status}`);
      }

      const files = await response.json();

      // Filter JSON files and fetch their contents
      const jsonFiles = files.filter(file => file.name.endsWith('.json'));
      filesData = await Promise.all(
        jsonFiles.map(async file => {
          // Use same headers for file content requests
          const resp = await fetch(file.download_url, { headers });
          if (!resp.ok) throw new Error(`Failed to load ${file.name}`);
          const data = await resp.json();
          return { name: file.name.replace(/\.json$/i, ''), data };
        })
      );
    } else {
      // Local implementation
      const listResponse = await fetch(dataPath + '/');
      const listText = await listResponse.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(listText, 'text/html');
      const links = Array.from(doc.querySelectorAll('a'))
          .map(a => a.getAttribute('href'))
          .filter(href => href && href.endsWith('.json'));

      filesData = await Promise.all(links.map(async file => {
          const resp = await fetch(`${dataPath}/${file}`);
          if (!resp.ok) throw new Error(`Failed to load ${file}`);
          const data = await resp.json();
          return { name: file.replace(/\.json$/i, ''), data };
      }));
    }

    // Populate target object
    filesData.filter(item => item).forEach(({ name, data }) => {
      targetObject[name] = data;
    });

    console.log(`Loaded ${Object.keys(targetObject).length} model files`);

    // Execute success callback
    onSuccess(targetObject);

    return targetObject;
  } catch (error) {
    onError(error);
    throw error;
  }
}

/**
 * Load all JSON for the main application
 */
async function loadAllJSON() {
  try {
    // Show loading indicator
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('viewer').classList.add('hidden');
    document.getElementById('error').classList.add('hidden');

    // Load data
    await loadJSONData({
      targetObject: allData,
      onSuccess: (data) => {
        // Update global data
        allModels = Object.keys(data);

        // Hide loading indicator, show viewer
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('viewer').classList.remove('hidden');

        // Initial render of model grid
        renderModelGrid();

        // Default-select top 4 models by score
        const sorted = [...allModels].sort((a, b) => {
          const sa = data[a]?.score || 0;
          const sb = data[b]?.score || 0;
          return sb - sa;
        });
        const topModels = sorted.slice(0, 4);
        topModels.forEach(model => {
          selectedModels.add(model);
          if (!selectedCategories.includes(model)) {
            selectedCategories.push(model);
          }
        });

        // Re-render with selections
        renderModelGrid();
        renderSelectedTrees();
      },
      onError: (error) => {
        document.getElementById('loading').classList.add('hidden');
        const errEl = document.getElementById('error');
        errEl.classList.remove('hidden');
        errEl.textContent = `Error: ${error.message}`;
      }
    });
  } catch (error) {
    // Error already handled in onError callback
    console.error("Failed to load data:", error);
  }
}

/**
 * Load all query model data
 */
async function loadAllQueryModelData() {
  try {
    return await loadJSONData({
      targetObject: queryModelData,
      onError: (error) => {
        console.error("Failed to load model data:", error);
      }
    });
  } catch (error) {
    console.error("Failed to load query model data:", error);
    throw error;
  }
}

/**
 * Set GitHub token for API access
 * @param {string} token - The GitHub token
 */
function setGitHubToken(token) {
  githubToken = token;
  // After setting the token, you might want to retry loading if previous attempts failed
  if (Object.keys(allData).length === 0) {
    loadAllJSON();
  }
}

/**
 * Create token input UI and add it to the page
 */
function createTokenInputUI() {
  const tokenContainer = document.createElement('div');
  tokenContainer.className = 'token-container';
  tokenContainer.style.margin = '10px 0';

  const tokenInput = document.createElement('input');
  tokenInput.type = 'password';
  tokenInput.placeholder = 'GitHub Token (optional)';
  tokenInput.className = 'token-input';
  tokenInput.style.padding = '8px';
  tokenInput.style.marginRight = '10px';

  const tokenButton = document.createElement('button');
  tokenButton.textContent = 'Set Token';
  tokenButton.className = 'token-button';
  tokenButton.style.padding = '8px 16px';

  tokenButton.addEventListener('click', () => {
    setGitHubToken(tokenInput.value);
    if (tokenInput.value) {
      tokenButton.textContent = 'Token Set ✓';
      setTimeout(() => {
        tokenButton.textContent = 'Set Token';
      }, 3000);
    }
  });

  tokenContainer.appendChild(tokenInput);
  tokenContainer.appendChild(tokenButton);

  // Add to page - insert before the loading element
  const loadingEl = document.getElementById('loading');
  if (loadingEl && loadingEl.parentNode) {
    loadingEl.parentNode.insertBefore(tokenContainer, loadingEl);
  } else {
    // Fallback if loading element isn't found
    document.body.insertBefore(tokenContainer, document.body.firstChild);
  }
}

// Initialize the token input UI when the page loads
document.addEventListener('DOMContentLoaded', () => {
  createTokenInputUI();
  loadAllJSON(); // Start loading data
});

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
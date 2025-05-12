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

async function loadAllJSON() {
  try {
    // Check if we're running on GitHub Pages or locally
    const isGitHubPages = window.location.hostname.includes('github.io') ||
                         window.location.hostname.includes('liudan193.github.io');

    let filesData;

    if (isGitHubPages) {
      // GitHub Pages implementation
      const owner = 'liudan193';
      const repo = 'Feedbacker';
      const path = 'visualization_and_analysis/processed_data';

      // Try to get token from localStorage if available
      const token = localStorage.getItem('github_token');

      // Prepare headers for GitHub API
      const headers = {};
      if (token) {
        headers.Authorization = `token ${token}`;
      }

      // Fetch directory listing via GitHub API
      const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
      const response = await fetch(apiUrl, { headers });

      // Handle rate limit error
      if (response.status === 403) {
        const rateLimitMessage = await response.json();
        if (rateLimitMessage.message && rateLimitMessage.message.includes('rate limit')) {
          // Show token input dialog
          showTokenDialog();
          throw new Error('GitHub API rate limit exceeded. Please provide a personal access token and try again.');
        }
      }

      if (!response.ok) throw new Error(`GitHub API error: ${response.status}`);
      const files = await response.json();

      // Filter JSON files and fetch their contents
      const jsonFiles = files.filter(file => file.name.endsWith('.json'));
      filesData = await Promise.all(
        jsonFiles.map(async file => {
          // Use the same token for downloading files
          const resp = await fetch(file.download_url, { headers });
          if (!resp.ok) throw new Error(`Failed to load ${file.name}`);
          const data = await resp.json();
          return { name: file.name.replace(/\.json$/i, ''), data };
        })
      );
    } else {
      // Local implementation
      const listResponse = await fetch('processed_data/');
      const listText = await listResponse.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(listText, 'text/html');
      const links = Array.from(doc.querySelectorAll('a'))
          .map(a => a.getAttribute('href'))
          .filter(href => href && href.endsWith('.json'));

      filesData = await Promise.all(links.map(async file => {
          const resp = await fetch(`processed_data/${file}`);
          const data = await resp.json();
          return { name: file.replace(/\.json$/i, ''), data };
      }));
    }

    // Populate global data structures (same for both implementations)
    filesData.forEach(({ name, data }) => {
      allData[name] = data;
    });
    allModels = Object.keys(allData);

    // Hide loading indicator, show viewer
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('viewer').classList.remove('hidden');

    // Initial render of model grid
    renderModelGrid();

    // Default-select top 4 models by score
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

    // Re-render with selections
    renderModelGrid();
    renderSelectedTrees();

  } catch (error) {
    document.getElementById('loading').classList.add('hidden');
    const errEl = document.getElementById('error');
    errEl.classList.remove('hidden');
    errEl.textContent = `Error: ${error.message}`;
  }
}

async function loadAllQueryModelData() {
    try {
        // Check if we're running on GitHub Pages or locally
        const isGitHubPages = window.location.hostname.includes('github.io') ||
                             window.location.hostname.includes('liudan193.github.io');

        let filesData;

        if (isGitHubPages) {
            // GitHub Pages implementation
            const owner = 'liudan193';
            const repo = 'Feedbacker';
            const path = 'visualization_and_analysis/processed_data';

            // Try to get token from localStorage if available
            const token = localStorage.getItem('github_token');

            // Prepare headers for GitHub API
            const headers = {};
            if (token) {
              headers.Authorization = `token ${token}`;
            }

            // Fetch directory listing via GitHub API
            const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
            const response = await fetch(apiUrl, { headers });

            // Handle rate limit error
            if (response.status === 403) {
              const rateLimitMessage = await response.json();
              if (rateLimitMessage.message && rateLimitMessage.message.includes('rate limit')) {
                // Show token input dialog
                showTokenDialog();
                throw new Error('GitHub API rate limit exceeded. Please provide a personal access token and try again.');
              }
            }

            if (!response.ok) throw new Error(`GitHub API error: ${response.status}`);
            const files = await response.json();

            // Filter JSON files
            const jsonFiles = files.filter(file => file.name.endsWith('.json'));

            // Load each JSON file
            filesData = await Promise.all(jsonFiles.map(async file => {
                try {
                    // Use the same token for downloading files
                    const resp = await fetch(file.download_url, { headers });
                    if (!resp.ok) throw new Error(`Failed to load ${file.name}`);
                    const data = await resp.json();
                    return { name: file.name.replace(/\.json$/i, ''), data };
                } catch (err) {
                    console.error(`Error loading ${file.name}:`, err);
                    return null;
                }
            }));
        } else {
            // Local implementation
            const listResponse = await fetch('processed_data/');
            const listText = await listResponse.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(listText, 'text/html');

            // Get all links that might be JSON files
            const links = Array.from(doc.querySelectorAll('a'))
                .map(a => a.getAttribute('href'))
                .filter(href => href && typeof href === 'string' && href.toLowerCase().endsWith('.json'));

            // Load each JSON file
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

        // Add valid data to queryModelData (same for both implementations)
        filesData.forEach(item => {
            if (item) {
                queryModelData[item.name] = item.data;
            }
        });

        console.log(`Loaded ${Object.keys(queryModelData).length} model files`);
        return queryModelData;
    } catch (error) {
        console.error("Failed to load model data:", error);
        throw error;
    }
}

// Function to show token input dialog
function showTokenDialog() {
    // If dialog already exists, just show it
    let tokenDialog = document.getElementById('token-dialog');

    if (!tokenDialog) {
        // Create dialog elements
        tokenDialog = document.createElement('div');
        tokenDialog.id = 'token-dialog';
        tokenDialog.className = 'token-dialog';

        const dialogContent = document.createElement('div');
        dialogContent.className = 'token-dialog-content';

        // Add title
        const title = document.createElement('h2');
        title.textContent = 'GitHub API Rate Limit Exceeded';
        dialogContent.appendChild(title);

        // Add explanation
        const explanation = document.createElement('p');
        explanation.textContent = 'You have exceeded the GitHub API rate limit. Please provide a personal access token to continue.';
        dialogContent.appendChild(explanation);

        // Add link to GitHub token creation
        const tokenLink = document.createElement('p');
        tokenLink.innerHTML = 'You can create a token at <a href="https://github.com/settings/tokens" target="_blank">https://github.com/settings/tokens</a> (no special permissions needed).';
        dialogContent.appendChild(tokenLink);

        // Add input field
        const tokenInput = document.createElement('input');
        tokenInput.type = 'text';
        tokenInput.id = 'github-token';
        tokenInput.placeholder = 'Paste your GitHub token here';
        dialogContent.appendChild(tokenInput);

        // Add button container
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'button-container';

        // Add submit button
        const submitButton = document.createElement('button');
        submitButton.textContent = 'Save and Reload';
        submitButton.onclick = () => {
            const token = document.getElementById('github-token').value.trim();
            if (token) {
                localStorage.setItem('github_token', token);
                tokenDialog.style.display = 'none';
                window.location.reload(); // Refresh the page
            }
        };
        buttonContainer.appendChild(submitButton);

        // Add cancel button
        const cancelButton = document.createElement('button');
        cancelButton.textContent = 'Cancel';
        cancelButton.onclick = () => {
            tokenDialog.style.display = 'none';
        };
        buttonContainer.appendChild(cancelButton);

        dialogContent.appendChild(buttonContainer);

        tokenDialog.appendChild(dialogContent);
        document.body.appendChild(tokenDialog);

        // Add dialog styling
        const style = document.createElement('style');
        style.textContent = `
            .token-dialog {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            
            .token-dialog-content {
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                max-width: 500px;
                width: 80%;
            }
            
            .token-dialog h2 {
                margin-top: 0;
            }
            
            .token-dialog input {
                width: 100%;
                padding: 8px;
                margin: 10px 0;
                box-sizing: border-box;
            }
            
            .button-container {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                margin-top: 15px;
            }
            
            .button-container button {
                padding: 8px 12px;
                cursor: pointer;
            }
        `;
        document.head.appendChild(style);
    }

    // Show the dialog
    tokenDialog.style.display = 'flex';
}

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
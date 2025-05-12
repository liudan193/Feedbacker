let allData = {};
let allModels = [];
const selectedCategories = [];
let selectedModels = new Set();
let queryModelData = {};
let githubToken = ''; // Variable to store GitHub token

function initializeModelView() {
    setupModelSelector();
    loadAllData();
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

async function loadAllData() {
  try {
    // 检查是否在 GitHub Pages 或本地运行
    const isGitHubPages = window.location.hostname.includes('github.io') ||
                         window.location.hostname.includes('liudan193.github.io');

    let filesData;

    if (isGitHubPages) {
      // GitHub Pages 实现
      const owner = 'liudan193';
      const repo = 'Feedbacker';
      const path = 'visualization_and_analysis/processed_data';

      // 使用CORS代理服务
      const corsProxy = 'https://corsproxy.io/?';
      let apiUrl = `${corsProxy}https://api.github.com/repos/${owner}/${repo}/contents/${path}`;

      // 添加token（如可用）
      const headers = {};
      if (githubToken) {
        headers.Authorization = `token ${githubToken}`;
      }

      const response = await fetch(apiUrl, { headers });

      // 处理403错误（超出速率限制）
      if (response.status === 403) {
        showTokenInputDialog();
        throw new Error('GitHub API 速率限制已超出。请提供令牌。');
      }

      if (!response.ok) throw new Error(`GitHub API 错误: ${response.status}`);

      const files = await response.json();

      // 过滤JSON文件并获取其内容
      const jsonFiles = files.filter(file => file.name.endsWith('.json'));
      filesData = await Promise.all(
        jsonFiles.map(async file => {
          // 同样使用CORS代理获取文件内容
          const fileUrl = `${corsProxy}${file.download_url}`;
          const resp = await fetch(fileUrl, { headers });
          if (!resp.ok) throw new Error(`加载 ${file.name} 失败`);
          const data = await resp.json();
          return { name: file.name.replace(/\.json$/i, ''), data };
        })
      );
    } else {
      // 本地实现
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

    // 处理数据（两种用例）
    filesData.forEach(({ name, data }) => {
      allData[name] = data;
      queryModelData[name] = data; // 同时填充 queryModelData
    });
    allModels = Object.keys(allData);

    console.log(`已加载 ${Object.keys(allData).length} 个模型文件`);

    // 隐藏加载指示器，显示查看器
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('viewer').classList.remove('hidden');

    // 初始渲染模型网格
    renderModelGrid();

    // 默认选择按得分排名前4的模型
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

    // 使用选择重新渲染
    renderModelGrid();
    renderSelectedTrees();

    return { allData, queryModelData };

  } catch (error) {
    document.getElementById('loading').classList.add('hidden');
    const errEl = document.getElementById('error');
    errEl.classList.remove('hidden');
    errEl.textContent = `错误: ${error.message}`;
    throw error;
  }
}

// Function to show GitHub token input dialog
function showTokenInputDialog() {
  // Create modal if it doesn't exist
  let modal = document.getElementById('tokenModal');

  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'tokenModal';
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="modal-content">
        <h2>GitHub API Rate Limit Exceeded</h2>
        <p>To continue accessing data from GitHub, please provide a GitHub personal access token:</p>
        <input type="text" id="githubTokenInput" placeholder="Paste your GitHub token here">
        <div class="modal-buttons">
          <button id="submitToken">Submit</button>
          <button id="cancelToken">Cancel</button>
        </div>
        <p class="modal-info">You can create a token at <a href="https://github.com/settings/tokens" target="_blank">GitHub Token Settings</a></p>
      </div>
    `;

    document.body.appendChild(modal);

    // Add event listeners
    document.getElementById('submitToken').addEventListener('click', () => {
      githubToken = document.getElementById('githubTokenInput').value.trim();
      modal.style.display = 'none';
      loadAllData(); // Retry loading with the token
    });

    document.getElementById('cancelToken').addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  modal.style.display = 'block';
}

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

// shared.js code
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

    // Node header
    const nodeHeader = document.createElement('div');
    nodeHeader.className = 'tree-node-header';
    nodeHeader.textContent = nodeData.name;

    // Path handling
    const path = [...currentPath, nodeData.key].join('.');

    // Click event
    nodeHeader.addEventListener('click', (e) => {
        e.stopPropagation();
        nodeHeader.classList.toggle('selected');
        updateSelection(path, nodeHeader.classList.contains('selected'));
        renderRankings();
    });

    node.appendChild(nodeHeader);

    // Recursive child nodes
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
        // Create column container
        const column = document.createElement('div');
        column.className = 'ranking-column';

        // Column header
        const header = document.createElement('div');
        header.className = 'ranking-header';
        header.textContent = path.split('.').pop();
        column.appendChild(header);

        // Get and sort data
        const rankings = allModels.map(model => ({
            model,
            ranking: getNestedValue(allData[model], path)?.ranking || Infinity
        })).sort((a, b) => a.ranking - b.ranking);

        // Fill ranking data
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

// Add CSS for the modal
const modalStyle = document.createElement('style');
modalStyle.textContent = `
.modal {
  display: none;
  position: fixed;
  z-index: 1000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
}

.modal-content {
  background-color: #fff;
  margin: 15% auto;
  padding: 20px;
  border-radius: 5px;
  width: 80%;
  max-width: 500px;
}

.modal-buttons {
  margin-top: 20px;
  text-align: right;
}

.modal-buttons button {
  margin-left: 10px;
  padding: 8px 16px;
  cursor: pointer;
}

.modal-info {
  margin-top: 15px;
  font-size: 0.9em;
  color: #666;
}
`;
document.head.appendChild(modalStyle);
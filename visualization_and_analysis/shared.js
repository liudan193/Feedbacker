let githubToken = '';
let allData = {};
let allModels = [];
const selectedCategories = [];
let selectedModels = new Set();
let queryModelData = {};

function setGithubToken(token) {
    githubToken = token;
}

async function loadJSONFiles(path) {
    try {
        const isGitHubPages = window.location.hostname.includes('github.io') ||
                             window.location.hostname.includes('liudan193.github.io');

        let filesData;

        if (isGitHubPages) {
            const owner = 'liudan193';
            const repo = 'Feedbacker';
            const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;

            const headers = githubToken ? { Authorization: `token ${githubToken}` } : {};
            const response = await fetch(apiUrl, { headers });

            if (!response.ok) {
                if (response.status === 403) {
                    document.getElementById('tokenInput').classList.remove('hidden');
                    throw new Error('GitHub API rate limit exceeded. Please enter a GitHub Token.');
                }
                throw new Error(`GitHub API error: ${response.status}`);
            }

            const files = await response.json();
            const jsonFiles = files.filter(file => file.name.endsWith('.json'));

            filesData = await Promise.all(
                jsonFiles.map(async file => {
                    const resp = await fetch(file.download_url);
                    if (!resp.ok) throw new Error(`Failed to load ${file.name}`);
                    const data = await resp.json();
                    return { name: file.name.replace(/\.json$/i, ''), data };
                })
            );
        } else {
            const listResponse = await fetch(path);
            const listText = await listResponse.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(listText, 'text/html');
            const links = Array.from(doc.querySelectorAll('a'))
                .map(a => a.getAttribute('href'))
                .filter(href => href && href.endsWith('.json'));

            filesData = await Promise.all(
                links.map(async file => {
                    const resp = await fetch(`${path}/${file}`);
                    const data = await resp.json();
                    return { name: file.replace(/\.json$/i, ''), data };
                })
            );
        }

        return filesData;
    } catch (error) {
        console.error("Failed to load JSON files:", error);
        throw error;
    }
}

async function loadAllJSON() {
    try {
        const filesData = await loadJSONFiles('visualization_and_analysis/processed_data');
        filesData.forEach(({ name, data }) => {
            allData[name] = data;
        });
        allModels = Object.keys(allData);

        document.getElementById('loading').classList.add('hidden');
        document.getElementById('viewer').classList.remove('hidden');

        renderModelGrid();

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
        const filesData = await loadJSONFiles('visualization_and_analysis/processed_data');
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

    const sortedModels = [...allModels].sort((a, b) => {
        const scoreA = allData[a]?.score || 0;
        const scoreB = allData[b]?.score || 0;
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
                const idx = selectedCategories.indexOf(model);
                if (idx > -1) {
                    selectedCategories.splice(idx, 1);
                }
            } else {
                selectedModels.add(model);
                modelItem.classList.add('selected');
                if (!selectedCategories.includes(model)) {
                    selectedCategories.push(model);
                }
            }
            renderSelectedTrees();
        });

        modelGrid.appendChild(modelItem);
    });
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

    const nodeHeader = document.createElement('div');
    nodeHeader.className = 'tree-node-header';
    nodeHeader.textContent = nodeData.name;

    const path = [...currentPath, nodeData.key].join('.');

    nodeHeader.addEventListener('click', (e) => {
        e.stopPropagation();
        nodeHeader.classList.toggle('selected');
        updateSelection(path, nodeHeader.classList.contains('selected'));
        renderRankings();
    });

    node.appendChild(nodeHeader);

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
        const column = document.createElement('div');
        column.className = 'ranking-column';

        const header = document.createElement('div');
        header.className = 'ranking-header';
        header.textContent = path.split('.').pop();
        column.appendChild(header);

        const rankings = allModels.map(model => ({
            model,
            ranking: getNestedValue(allData[model], path)?.ranking || Infinity
        })).sort((a, b) => a.ranking - b.ranking);

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

document.getElementById('submitToken').addEventListener('click', () => {
    const token = document.getElementById('tokenField').value.trim();
    if (token) {
        setGithubToken(token);
        document.getElementById('tokenInput').classList.add('hidden');
        loadAllJSON();
        loadAllQueryModelData();
    }
});

initializeModelView();
initializeQueryView();
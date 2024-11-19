// Maximum number of titles to display per class
const maxTitlesPerClass = 70;

// Maximum number of subtitles to display per title
const maxSubtitles = 15;

// Variable to control whether subtitles are displayed, default to false
let showSubtitles = false;

// Data structures for processed data with and without subtitles
let dataWithSubtitles = { "name": "🐒", "children": [] };
let dataWithoutSubtitles = { "name": "🐒", "children": [] };

// Create a tooltip element
const tooltip = d3.select("body")
    .append("div")
    .style("position", "absolute")
    .style("visibility", "hidden")
    .style("background", "#f9f9f9")
    .style("border", "1px solid #ccc")
    .style("border-radius", "5px")
    .style("padding", "8px")
    .style("font-size", "12px")
    .style("color", "#333");

// Fetch JSON data and process it into two separate structures
d3.json("../docs/titles.json").then(rawData => {
    // Process data with subtitles
    dataWithSubtitles.children = processData(rawData, true);
    // Process data without subtitles
    dataWithoutSubtitles.children = processData(rawData, false);
    
    // Initially draw the tree without subtitles
    drawRadialTidyTree(dataWithoutSubtitles);
});

// Function to process rawData based on whether subtitles should be included
function processData(rawData, includeSubtitles) {
    const classes = {};

    // Process data to group by class and merge duplicate titles/subtitles
    rawData.forEach(item => {
        const { class: cls, title, subtitle } = item;
        if (!classes[cls]) {
            classes[cls] = { name: cls, children: [] };
        }

        // Check if we have reached the max titles for this class
        if (classes[cls].children.length < maxTitlesPerClass) {
            const titleNode = classes[cls].children.find(child => child.name === title);
            
            if (titleNode) {
                // Add subtitles only if includeSubtitles is true and subtitle exists
                if (includeSubtitles && subtitle && titleNode.children.length < maxSubtitles && !titleNode.children.some(child => child.name === subtitle)) {
                    titleNode.children.push({ name: subtitle });
                }
            } else {
                // Add new title with subtitle if includeSubtitles is true and subtitle exists
                if (includeSubtitles && subtitle) {
                    classes[cls].children.push({ name: title, children: [{ name: subtitle }] });
                } else {
                    classes[cls].children.push({ name: title });
                }
            }
        }
    });

    // Return processed children data for the root
    return Object.values(classes);
}

function sendDataToOtherFrame(data) {
    // send data to the frame through parent.frames 
    window.parent.postMessage(data, '*');
    console.log("sent");
}


// // Create a new WebSocket connection to the server
// const socket = new WebSocket('ws://localhost:8765');

// // Event handler for when the connection is successfully opened
// socket.addEventListener('open', function (event) {
//     console.log('WebSocket connection established with the server');

//     // Send an initial greeting message to the server
//     // socket.send('Hello from the client!');
// });

// // Event handler for when a message is received from the server
// socket.addEventListener('message', function (event) {
//     console.log('Received message from server:', event.data);
// });

// // Event handler for when the connection is closed
// socket.addEventListener('close', function (event) {
//     console.log('WebSocket connection closed');
// });

// // Event handler for any errors that occur
// socket.addEventListener('error', function (error) {
//     console.error('WebSocket error:', error);
// });

// function sendMessage(msg) {
//     if (socket.readyState === WebSocket.OPEN) {
//         socket.send(msg);
//         console.log('Sent message to the server:', msg);
//     }
// }

// Function to draw the Radial Tidy Tree
function drawRadialTidyTree(data) {
    const width = 1000, height = 1000, radius = width / 2;
    const tree = d3.tree().size([2 * Math.PI, radius - 120]);

    const root = d3.hierarchy(data);
    tree(root);

    const svg = d3.select("svg")
        .append("g")
        .attr("transform", `translate(${width / 2},${height / 2})`);

    const link = svg.append("g")
        .selectAll("path")
        .data(root.links())
        .join("path")
        .attr("class", "link")
        .attr("d", d3.linkRadial()
            .angle(d => d.x)
            .radius(d => d.y))
        .style("stroke", d => {
            if (d.source.depth === 0) {
                return colorClass(d.target.data.name);
            } else {
                return colorClass(d.source.ancestors().find(a => a.depth === 1)?.data.name);
            }
        });

    const node = svg.append("g")
        .selectAll("g")
        .data(root.descendants())
        .join("g")
        .attr("transform", d => `
            rotate(${d.x * 180 / Math.PI - 90})
            translate(${d.y},0)
        `);

    node.append("circle")
        .attr("r", 5)
        .style("fill", d => colorClass(d.ancestors().find(a => a.depth === 1)?.data.name))
        .style("opacity", 0.3);

    // Add title text with tooltip display on hover
    node.append("text")
        .attr("dy", "0.31em")
        .attr("x", d => d.depth === 0 ? 0 : (d.x < Math.PI === !d.children ? 6 : -6))
        .attr("text-anchor", d => d.depth === 0 ? "middle" : (d.x < Math.PI === !d.children ? "start" : "end"))
        .attr("transform", d => d.depth === 0 ? "rotate(-90)" : (d.x >= Math.PI ? "rotate(180)" : null))
        .style("font-size", d => {
            if (d.depth === 0) return "25px";
            if (d.depth === 1) return "12px";
            return "5px";
        })
        .style("fill", d => colorClass(d.ancestors().find(a => a.depth === 1)?.data.name))
        .style("cursor", "pointer")
        .style("opacity", 0)
        .text(d => d.data.name.slice(0, 15))
        .on("mouseover", function(event, d) {
            const className = d.ancestors().find(a => a.depth === 1)?.data.name || "";
            const titleName = d.data.name;
            
            tooltip.html(`<strong>Class:</strong> ${className}<br><strong>Title:</strong> ${titleName}`)
                .style("visibility", "visible")
                .style("top", (event.pageY + 15) + "px")
                .style("left", (event.pageX + 15) + "px");

            d3.select(this)
                .style("font-size", d => {
                    if (d.depth === 0) return "25px";
                    if (d.depth === 1) return "12px";
                    return "7px";
                })
                .style("text-decoration", "underline");
        })
        .on("mouseout", function() {
            d3.select(this)
                .style("font-size", d => {
                    if (d.depth === 0) return "25px";
                    if (d.depth === 1) return "12px";
                    return "5px";
                })
                .style("text-decoration", "none");

            tooltip.style("visibility", "hidden");
        })
        .on("click", function(event, d) {
            console.log(d.data.name);
            // sendDataToOtherFrame(d.data.name);
            // sendMessage(d.data.name);
            // parent.sharedData = d.data.name;
            // console.log(parent.sharedData);
            window.parent.frames["firstIframe"].postMessage(d.data.name, "http://127.0.0.1:5000");
        })
        .clone(true).lower()
        .attr("stroke", "white");

    svg.selectAll("text")
        .transition()
        .duration(800)
        .style("opacity", 1);

    svg.selectAll("circle")
        .style("opacity", 0)
        .transition()
        .duration(800)
        .style("opacity", 0.3);
}

// Function to handle color assignment by class
function colorClass(name) {
    const colors = {
        "攻略": "#1f77b4",
        "下载": "#ff7f0e",
        "新闻": "#2ca02c"
    };
    return colors[name] || "#000";
}

// Toggle subtitles on button click
d3.select("#toggle-subtitles").on("click", () => {
    showSubtitles = !showSubtitles;
    d3.select("#toggle-subtitles").text(showSubtitles ? "Hide Subtitles" : "Show Subtitles");
    d3.select("svg").selectAll("*").remove();
    drawRadialTidyTree(showSubtitles ? dataWithSubtitles : dataWithoutSubtitles);
});

import logging
import os
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from src.config.paths import PathConfig


class Visualizer:
    """
    Generates data visualizations for bid documents.
    Includes Gantt charts for schedules and Organization charts for staffing.
    """
    def __init__(self, output_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.output_dir = output_dir or str(PathConfig.BID_DOCUMENTS_DIR / "assets")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_gantt_chart(self, tasks: list[dict[str, Any]], filename: str = "gantt_chart.png") -> str | None:
        """
        Generate a Gantt chart from a list of tasks.
        Task format: {"task": "Name", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
        """
        if not tasks:
            return None

        df = pd.DataFrame(tasks)
        df['start'] = pd.to_datetime(df['start'])
        df['end'] = pd.to_datetime(df['end'])
        df['duration'] = (df['end'] - df['start']).dt.days

        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot bars
        for _i, task in df.iterrows():
            start_date = mdates.date2num(task['start'])
            ax.barh(task['task'], task['duration'], left=start_date, height=0.5, align='center', color='#3b82f6')

        # Format axis
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.title("Implementation Schedule")
        plt.xlabel("Date")
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300)
        plt.close()

        self.logger.info(f"Generated Gantt chart: {filepath}")
        return filepath

    def generate_org_chart(self, staff: list[dict[str, Any]], filename: str = "org_chart.png") -> str | None:
        """
        Generate a simple hierarchical Org chart.
        Staff format: {"name": "Name", "role": "Role", "reports_to": "ManagerRole"}
        """
        if not staff:
            return None

        G = nx.DiGraph()
        labels = {}

        for person in staff:
            label = f"{person['role']}\n{person['name']}"
            G.add_node(person['role'], label=label)
            labels[person['role']] = label

            if person.get('reports_to'):
                G.add_edge(person['reports_to'], person['role'])

        pos = self._hierarchy_pos(G)

        plt.figure(figsize=(12, 8))
        nx.draw(G, pos, with_labels=False, node_size=5000, node_color="#e2e8f0", node_shape="s", edge_color="#64748b")
        nx.draw_networkx_labels(G, pos, labels, font_size=8)

        plt.title("Project Organization")
        plt.axis('off')

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300)
        plt.close()

        self.logger.info(f"Generated Org chart: {filepath}")
        return filepath

    def _hierarchy_pos(self, G, root=None, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5):
        """
        If there is a cycle that is reachable from root, then result will not be a hierarchy.
        G: the graph (must be a tree)
        root: the root node of current branch 
        width: horizontal space allocated for this branch - avoids overlap with other branches
        vert_gap: gap between levels of hierarchy
        vert_loc: vertical location of root
        xcenter: horizontal location of root
        """
        if not nx.is_tree(G):
             # Fallback layout if not a tree
             return nx.spring_layout(G)

        if root is None:
            if isinstance(G, nx.DiGraph):
                roots = [n for n in G.nodes() if G.in_degree(n) == 0]
                if roots:
                    return self._hierarchy_pos(G, roots[0], width, vert_gap, vert_loc, xcenter)
                else:
                    return nx.spring_layout(G) # Cyclic or empty
            else:
                return nx.spring_layout(G)

        def _hierarchy_pos_recursive(G, root, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5, pos = None, parent = None):
            if pos is None:
                pos = {root:(xcenter,vert_loc)}
            else:
                pos[root] = (xcenter, vert_loc)
            children = list(G.neighbors(root))
            if not isinstance(G, nx.DiGraph) and parent is not None:
                children.remove(parent)
            if len(children) != 0:
                dx = width/len(children)
                nextx = xcenter - width/2 - dx/2
                for child in children:
                    nextx += dx
                    pos = _hierarchy_pos_recursive(G,child, width=dx, vert_gap=vert_gap,
                                        vert_loc=vert_loc-vert_gap, xcenter=nextx,
                                        pos=pos, parent=root)
            return pos

        return _hierarchy_pos_recursive(G, root, width, vert_gap, vert_loc, xcenter)

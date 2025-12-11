import matplotlib.pyplot as plt
import numpy as np
import os

def generate_energy_graph(output_dir="."):
    time_labels = [
        "Fajr - 10 AM",
        "10 AM - 1 PM",
        "1 PM - Asr",
        "After Asr",
        "After Maghrib",
        "After Isha"
    ]
    # Energy levels based on the descriptions (0-5 scale)
    energy_levels = [5, 4, 4, 3, 1, 0]

    # Create positions for the bars
    x_pos = np.arange(len(time_labels))

    plt.figure(figsize=(10, 6))
    plt.bar(x_pos, energy_levels, align='center', alpha=0.7, color='skyblue')
    plt.xticks(x_pos, time_labels, rotation=45, ha="right")
    plt.ylabel('Energy Level (0-5 Stars)')
    plt.title('Daily Energy Graph')
    plt.ylim(0, 5.5) # Set y-axis limit slightly above max energy level

    # Add energy values on top of the bars
    for i, level in enumerate(energy_levels):
        plt.text(x_pos[i], level + 0.1, str(level), ha='center', va='bottom')

    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout() # Adjust layout to prevent labels from overlapping

    output_path = os.path.join(output_dir, "energy_graph.png")
    plt.savefig(output_path)
    print(f"Energy graph saved to {output_path}")

if __name__ == "__main__":
    # Ensure the output directory exists, or just save in the current script directory
    # For this exercise, saving it in the same directory as the script.
    generate_energy_graph("printer_control")

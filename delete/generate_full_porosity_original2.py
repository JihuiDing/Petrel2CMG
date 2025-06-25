import numpy as np
from pathlib import Path

def CMG_format_compress(array, max_line_length=80):
    """
    Compress a numpy array to CMG format (N*value).
    
    Args:
        array (numpy.ndarray): Input array to compress
        max_line_length (int): Maximum characters per line
        
    Returns:
        list: List of compressed lines
    """
    compressed_lines = []
    current_line = ""
    
    # Find consecutive runs of the same value
    i = 0
    while i < len(array):
        value = array[i]
        count = 1
        
        # Count consecutive occurrences of the same value
        while i + count < len(array) and np.isclose(array[i + count], value, rtol=1e-10):
            count += 1
        
        # Create compressed token - format zero values as "0" instead of "0.000000"
        if np.isclose(value, 0.0, rtol=1e-10):
            if count == 1:
                token = "0"
            else:
                token = f"{count}*0"
        else:
            if count == 1:
                # token = f"{value:.6f}"
                token = f"{value}"
            else:
                # token = f"{count}*{value:.6f}"
                token = f"{count}*{value}"
        
        # Add to current line or start new line
        if current_line and len(current_line + " " + token) > max_line_length:
            compressed_lines.append(current_line)
            current_line = token
        else:
            if current_line:
                current_line += " " + token
            else:
                current_line = token
        
        i += count
    
    # Add the last line
    if current_line:
        compressed_lines.append(current_line)
    
    return compressed_lines

def generate_full_porosity(
        actid_file, 
        poro_file, 
        output_file,
        total_cells,
        use_compression=True,
        ):
    """
    Generate a porosity data file for all cells, filling inactive cells with 0.
    
    Args:
        actid_file (str or Path): Path to the active cell ID file (actid.npy)
        poro_file (str or Path): Path to the porosity file (poro.npy)
        output_file (str or Path): Path to the output porosity data file
        total_cells (int): Total number of cells in the grid (default: 989001)
        use_compression (bool): Whether to use compressed CMG format (default: True)
    
    Returns:
        dict: Summary statistics of the generated data
    """
    # Convert to Path objects
    actid_file = Path(actid_file)
    poro_file = Path(poro_file)
    output_file = Path(output_file)
    
    # Check if input files exist
    if not actid_file.exists():
        raise FileNotFoundError(f"Active cell ID file not found: {actid_file}")
    if not poro_file.exists():
        raise FileNotFoundError(f"Porosity file not found: {poro_file}")
    
    print(f"Loading active cell IDs from: {actid_file}")
    active_cell_ids = np.load(actid_file)
    
    print(f"Loading porosity values from: {poro_file}")
    porosity_values = np.load(poro_file)
    
    print(f"Active cell IDs shape: {active_cell_ids.shape}")
    print(f"Porosity values shape: {porosity_values.shape}")
    print(f"Active cell IDs data type: {active_cell_ids.dtype}")
    print(f"Porosity values data type: {porosity_values.dtype}")
    
    # Convert active cell IDs to integers if needed
    if active_cell_ids.dtype != np.int64 and active_cell_ids.dtype != np.int32:
        print("Converting active cell IDs to integers...")
        active_cell_ids = active_cell_ids.astype(np.int64)
    
    # Verify that the number of active cells matches the number of porosity values
    if len(active_cell_ids) != len(porosity_values):
        raise ValueError(f"Mismatch: {len(active_cell_ids)} active cells but {len(porosity_values)} porosity values")
    
    # Check that cell IDs are within valid range
    min_id = np.min(active_cell_ids)
    max_id = np.max(active_cell_ids)
    print(f"Active cell ID range: {min_id} to {max_id}")
    
    if min_id < 1 or max_id > total_cells:
        raise ValueError(f"Cell IDs out of range: {min_id} to {max_id} (should be 1 to {total_cells})")
    
    # Create full porosity array initialized with zeros
    print(f"Creating full porosity array for {total_cells:,} cells...")
    full_porosity = np.zeros(total_cells, dtype=np.float64)
    
    # Fill in porosity values for active cells
    print("Filling porosity values for active cells...")
    full_porosity[active_cell_ids - 1] = porosity_values  # Subtract 1 because cell IDs are 1-based
    
    # Calculate statistics
    active_count = len(active_cell_ids)
    inactive_count = total_cells - active_count
    active_porosity_mean = np.mean(porosity_values)
    active_porosity_min = np.min(porosity_values)
    active_porosity_max = np.max(porosity_values)
    
    # Save the full porosity array
    print(f"Saving full porosity data to: {output_file}")
    np.save(output_file, full_porosity)
    
    # Save in compressed CMG format
    if use_compression:
        compressed_output = output_file.parent / "compressed_por.dat"
        print(f"Compressing and saving to CMG format: {compressed_output}")
        
        # Create header
        header = "**POR *ALL"
        
        # Compress the array
        print("Compressing data to CMG format...")
        compressed_lines = CMG_format_compress(full_porosity)
        
        # Write compressed file
        with open(compressed_output, 'w') as f:
            f.write(header + '\n')
            for line in compressed_lines:
                f.write(line + '\n')
        
        print(f"Compressed {len(full_porosity):,} values into {len(compressed_lines)} lines")
        compression_ratio = len(full_porosity) / len(compressed_lines)
        print(f"Compression ratio: {compression_ratio:.1f}:1")
    
    # Create summary statistics
    summary = {
        'total_cells': total_cells,
        'active_cells': active_count,
        'inactive_cells': inactive_count,
        'active_cell_percentage': (active_count / total_cells) * 100,
        'active_porosity_mean': active_porosity_mean,
        'active_porosity_min': active_porosity_min,
        'active_porosity_max': active_porosity_max,
        'full_porosity_mean': np.mean(full_porosity),
        'full_porosity_min': np.min(full_porosity),
        'full_porosity_max': np.max(full_porosity),
        'output_file': str(output_file),
    }
    
    if use_compression:
        summary['compressed_file'] = str(compressed_output)
        summary['compression_ratio'] = compression_ratio
        summary['compressed_lines'] = len(compressed_lines)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total cells: {summary['total_cells']:,}")
    print(f"Active cells: {summary['active_cells']:,} ({summary['active_cell_percentage']:.2f}%)")
    print(f"Inactive cells: {summary['inactive_cells']:,}")
    print(f"Active porosity - Mean: {summary['active_porosity_mean']:.6f}")
    print(f"Active porosity - Min: {summary['active_porosity_min']:.6f}")
    print(f"Active porosity - Max: {summary['active_porosity_max']:.6f}")
    print(f"Full porosity - Mean: {summary['full_porosity_mean']:.6f}")
    print(f"Full porosity - Min: {summary['full_porosity_min']:.6f}")
    print(f"Full porosity - Max: {summary['full_porosity_max']:.6f}")
    print(f"Output file: {summary['output_file']}")
    if use_compression:
        print(f"Compressed file: {summary['compressed_file']}")
        print(f"Compression ratio: {summary['compression_ratio']:.1f}:1")
        print(f"Compressed lines: {summary['compressed_lines']:,}")
    print("="*60)
    
    return summary
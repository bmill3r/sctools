"""
Dimensionality Reduction Module for Single-Cell Analysis

This module provides the DimensionalityReduction class for performing various
dimensionality reduction techniques on single-cell RNA-seq data. It includes
implementations of PCA, UMAP, and t-SNE, with utilities for visualization and analysis
of the reduced-dimensional representations.

Dimensionality reduction is essential for visualizing and analyzing high-dimensional
single-cell data, revealing underlying structure and relationships between cells.

Key features:
    - Principal Component Analysis (PCA) with variance analysis
    - Uniform Manifold Approximation and Projection (UMAP)
    - t-Distributed Stochastic Neighbor Embedding (t-SNE)
    - Visualization of explained variance in PCA
    - Support for highly variable gene selection

Upstream dependencies:
    - SingleCellQC for quality control and filtering
    - Normalization for data normalization
    - FeatureSelection for identifying highly variable genes

Downstream applications:
    - EnhancedVisualization for advanced plotting
    - Clustering algorithms for cell type identification
    - Trajectory inference for developmental processes
"""

import numpy as np
import pandas as pd
import scanpy as sc
import anndata as ad
import matplotlib.pyplot as plt
from typing import Union, Optional, Tuple, Dict
import warnings


class DimensionalityReduction:
    """
    Class for dimensionality reduction of single-cell data.
    
    This class provides methods for reducing the dimensionality of single-cell RNA-seq 
    data using various techniques like PCA, UMAP, and t-SNE. These methods help visualize 
    and analyze high-dimensional gene expression data in lower-dimensional spaces.
    
    The DimensionalityReduction class typically follows normalization and feature selection
    steps in the single-cell analysis workflow:
    
    - Upstream dependencies:
      * SingleCellQC for quality control and filtering
      * Normalization for data normalization
      * FeatureSelection for identifying highly variable genes
    
    - Downstream applications:
      * EnhancedVisualization for advanced plotting of reduced dimensions
      * Clustering algorithms that operate on lower-dimensional representations
      * Trajectory inference for developmental processes
      * Cell type annotation based on reduced-dimensional space
    
    Attributes:
        adata (AnnData): AnnData object containing the single-cell data.
    
    Examples:
        >>> # After QC, normalization, and feature selection
        >>> from sctools.dim_reduction import DimensionalityReduction
        >>> dr = DimensionalityReduction(adata)
        >>> 
        >>> # Run PCA
        >>> dr.run_pca(n_comps=30)
        >>> 
        >>> # Visualize PCA variance
        >>> dr.plot_pca_variance(threshold=0.8)
        >>> 
        >>> # Compute neighbors and run UMAP
        >>> sc.pp.neighbors(dr.adata, n_neighbors=15, n_pcs=30)
        >>> dr.run_umap()
        >>> 
        >>> # Use the embedded data for downstream analysis
        >>> embedded_adata = dr.adata
    """
    
    def __init__(self, adata: ad.AnnData):
        """
        Initialize with AnnData object.
        
        Parameters:
            adata (AnnData): AnnData object containing gene expression data.
            
        Examples:
            >>> dr = DimensionalityReduction(adata)
        """
        self.adata = adata
        
    def run_pca(self, 
              n_comps: int = 50,
              use_highly_variable: bool = True,
              svd_solver: str = 'arpack',
              random_state: int = 42,
              return_info: bool = False,
              inplace: bool = True) -> Optional[Union[ad.AnnData, Tuple[ad.AnnData, Dict]]]:
        """
        Run Principal Component Analysis (PCA) on the data.
        
        This method performs PCA on the gene expression data, optionally focusing
        on highly variable genes. PCA is typically the first dimensionality reduction
        step in single-cell analysis, serving as input for further methods like UMAP.
        
        Parameters:
            n_comps : int
                Number of principal components to compute.
            use_highly_variable : bool
                Whether to use highly variable genes only.
            svd_solver : str
                SVD solver to use ('arpack', 'randomized', 'auto', etc.).
            random_state : int
                Random seed for reproducibility.
            return_info : bool
                Whether to return PCA information dictionary.
            inplace : bool
                If True, modify self.adata, else return a copy.
                
        Returns:
            Optional[Union[AnnData, Tuple[AnnData, Dict]]]
                If inplace is False, returns AnnData with PCA results.
                If return_info is True, also returns PCA information dictionary.
                
        Examples:
            >>> dr = DimensionalityReduction(adata)
            >>> 
            >>> # Basic PCA with 30 components
            >>> dr.run_pca(n_comps=30)
            >>> 
            >>> # PCA with 50 components and return info
            >>> pca_info = dr.run_pca(n_comps=50, return_info=True)
            >>> print(f"Variance explained: {pca_info['variance_ratio'].sum():.2%}")
            >>> 
            >>> # Run PCA on all genes
            >>> dr.run_pca(use_highly_variable=False)
        
        Notes:
            - Stores the PCA results in adata.obsm['X_pca']
            - Stores the PC loadings in adata.varm['PCs'] if available
            - Stores PCA info (variance, etc.) in adata.uns['pca']
            - If use_highly_variable=True, only uses genes marked as highly variable
        """
        print(f"Running PCA with {n_comps} components")
        
        # Create a copy if not inplace
        adata = self.adata if inplace else self.adata.copy()
        
        # Check for highly variable genes if requested
        if use_highly_variable and 'highly_variable' in adata.var.columns:
            print(f"Using {sum(adata.var.highly_variable)} highly variable genes for PCA")
            adata_use = adata[:, adata.var.highly_variable]
        else:
            adata_use = adata
            
        # Run PCA
        sc.tl.pca(
            adata_use,
            n_comps=n_comps,
            svd_solver=svd_solver,
            random_state=random_state,
            return_info=return_info
        )
        
        # Copy PCA results to the original object if using HVGs
        if use_highly_variable and 'highly_variable' in adata.var.columns:
            adata.obsm['X_pca'] = adata_use.obsm['X_pca']
            if 'PCs' in adata_use.varm:
                adata.varm['PCs'] = np.zeros((adata.shape[1], n_comps))
                adata.varm['PCs'][adata.var.highly_variable] = adata_use.varm['PCs']
            if hasattr(adata_use, 'uns') and 'pca' in adata_use.uns:
                adata.uns['pca'] = adata_use.uns['pca']
        
        # Update the instance
        if inplace:
            self.adata = adata
            if return_info and 'pca' in adata.uns:
                return adata.uns['pca']
        else:
            if return_info and 'pca' in adata.uns:
                return adata, adata.uns['pca']
            return adata
    
    def plot_pca_variance(self, 
                        n_pcs: int = 50,
                        log: bool = False,
                        threshold: Optional[float] = None,
                        figsize: Tuple[float, float] = (10, 4),
                        save_path: Optional[str] = None,
                        return_fig: bool = False) -> Optional[plt.Figure]:
        """
        Plot the explained variance ratio of principal components.
        
        This method visualizes the variance explained by each principal component
        and the cumulative explained variance. It helps determine how many PCs
        to use for downstream analysis.
        
        Parameters:
            n_pcs : int
                Number of principal components to plot.
            log : bool
                Whether to use log scale for y-axis.
            threshold : Optional[float]
                If specified, draw a horizontal line at this cumulative explained variance threshold.
            figsize : Tuple[float, float]
                Figure size.
            save_path : Optional[str]
                Path to save the figure. If None, the figure is displayed.
            return_fig : bool
                If True, return the figure object.
                
        Returns:
            Optional[plt.Figure]
                Figure object if return_fig is True.
                
        Raises:
            ValueError: If PCA hasn't been performed yet.
                
        Examples:
            >>> dr = DimensionalityReduction(adata)
            >>> dr.run_pca(n_comps=50)
            >>> 
            >>> # Plot variance explained by each PC
            >>> dr.plot_pca_variance()
            >>> 
            >>> # Plot with threshold line at 90% explained variance
            >>> dr.plot_pca_variance(threshold=0.9)
            >>> 
            >>> # Save the plot to a file
            >>> dr.plot_pca_variance(save_path="pca_variance.png")
        
        Notes:
            - This visualization helps determine the appropriate number of PCs to retain
            - If threshold is provided, shows how many PCs are needed to reach that level of explained variance
            - Using log=True can help visualize the tail of the distribution
        """
        if 'pca' not in self.adata.uns or 'variance_ratio' not in self.adata.uns['pca']:
            raise ValueError("PCA hasn't been performed yet or variance_ratio information is missing.")
            
        # Get variance data
        variance_ratio = self.adata.uns['pca']['variance_ratio']
        variance_cumsum = np.cumsum(variance_ratio)
        
        # Limit to n_pcs
        n_pcs = min(n_pcs, len(variance_ratio))
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # Plot variance explained by each PC
        ax1.plot(range(1, n_pcs + 1), variance_ratio[:n_pcs] * 100, 'o-')
        ax1.set_xlabel('Principal Component')
        ax1.set_ylabel('Explained Variance Ratio (%)')
        if log:
            ax1.set_yscale('log')
        ax1.set_title('PCA Explained Variance')
        ax1.set_xticks(range(1, n_pcs + 1, 5))
        ax1.grid(True)
        
        # Plot cumulative variance explained
        ax2.plot(range(1, n_pcs + 1), variance_cumsum[:n_pcs] * 100, 'o-')
        ax2.set_xlabel('Number of Principal Components')
        ax2.set_ylabel('Cumulative Explained Variance (%)')
        ax2.set_title('PCA Cumulative Explained Variance')
        ax2.set_xticks(range(1, n_pcs + 1

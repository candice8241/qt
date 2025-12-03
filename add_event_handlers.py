# 辅助脚本：将事件处理器代码添加到auto_fitting_module_v2.py

event_handlers = '''
    # ==================== Event Handlers (lines 986-1152) ====================
    
    def on_scroll(self, event):
        """Handle mouse scroll for zooming (lines 988-1011)"""
        if event.inaxes != self.ax or self.x is None:
            return
        
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        
        scale_factor = 0.8 if event.button == 'up' else 1.25
        
        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor
        
        relx = (xdata - xlim[0]) / (xlim[1] - xlim[0])
        rely = (ydata - ylim[0]) / (ylim[1] - ylim[0])
        
        new_xlim = [xdata - new_width * relx, xdata + new_width * (1 - relx)]
        new_ylim = [ydata - new_height * rely, ydata + new_height * (1 - rely)]
        
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw()
    
    def on_mouse_move(self, event):
        """Display mouse coordinates (lines 1013-1018)"""
        if event.inaxes == self.ax and event.xdata is not None:
            self.coord_label.setText(f"2theta: {event.xdata:.4f}  Intensity: {event.ydata:.2f}")
        else:
            self.coord_label.setText("")
    
    def on_click(self, event):
        """Handle mouse clicks (lines 1020-1036)"""
        if event.inaxes != self.ax or self.x is None:
            return
        
        if self.toolbar.mode != '':
            return
        
        x_click = event.xdata
        idx = np.argmin(np.abs(self.x - x_click))
        point_x = self.x[idx]
        point_y = self.y[idx]
        
        if self.selecting_bg:
            self._handle_bg_click(event, idx, point_x, point_y, x_click)
        elif not self.fitted:
            self._handle_peak_click(event, idx, point_x, point_y, x_click)
    
    def _handle_bg_click(self, event, idx, point_x, point_y, x_click):
        """Handle clicks in background selection mode (lines 1038-1084)"""
        if event.button == 1:  # Left click - add point
            marker, = self.ax.plot(point_x, point_y, 's', color='#4169E1',
                                  markersize=5, markeredgecolor='#FFD700',
                                  markeredgewidth=1.5, zorder=10)
            text = self.ax.text(point_x, point_y * 0.97, f'BG{len(self.bg_points)+1}',
                               ha='center', fontsize=5, color='#4169E1',
                               fontweight='bold', zorder=11)
            self.bg_points.append((point_x, point_y))
            self.bg_markers.append((marker, text))
            self.update_bg_connect_line()
            self.canvas.draw()
            
            self.undo_stack.append(('bg_point', len(self.bg_points) - 1))
            self.btn_undo.setEnabled(True)
            self.update_info(f"BG point {len(self.bg_points)} added at 2theta = {point_x:.4f}\\n")
            
            if len(self.bg_points) >= 2:
                self.btn_subtract_bg.setEnabled(True)
        
        elif event.button == 3:  # Right click - remove point
            if len(self.bg_points) > 0:
                # Find nearest background point
                distances = [abs(x_click - p[0]) for p in self.bg_points]
                delete_idx = np.argmin(distances)
                
                removed_point = self.bg_points.pop(delete_idx)
                marker_tuple = self.bg_markers.pop(delete_idx)
                
                try:
                    marker_tuple[0].remove()
                    marker_tuple[1].remove()
                except:
                    pass
                
                # Update labels
                for i, (marker, text) in enumerate(self.bg_markers):
                    text.set_text(f'BG{i+1}')
                
                self.update_bg_connect_line()
                self.canvas.draw()
                
                self.update_info(f"BG point removed at 2theta = {removed_point[0]:.4f}\\n")
                
                if len(self.bg_points) < 2:
                    self.btn_subtract_bg.setEnabled(False)
'''

print(event_handlers)

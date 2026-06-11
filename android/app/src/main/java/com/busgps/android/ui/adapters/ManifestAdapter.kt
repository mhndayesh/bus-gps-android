package com.busgps.android.ui.adapters

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemManifestBinding
import com.busgps.android.model.ManifestItem

class ManifestAdapter(
    private val items: List<ManifestItem>,
    private val onBoard: (String) -> Unit,
    private val onDrop: (String) -> Unit
) : RecyclerView.Adapter<ManifestAdapter.VH>() {

    inner class VH(val binding: ItemManifestBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemManifestBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        holder.binding.apply {
            tvStudentName.text = item.name
            val statusText = when (item.status) {
                "BOARDED" -> "On Bus"
                "DROPPED" -> "Dropped Off"
                else      -> "Waiting"
            }
            tvStudentStatus.text = statusText
            tvStudentStatus.setTextColor(when (item.status) {
                "BOARDED" -> 0xFF4CAF50.toInt()
                "DROPPED" -> 0xFF2196F3.toInt()
                else      -> 0xFF9E9E9E.toInt()
            })
            btnBoard.setOnClickListener { onBoard(item.id) }
            btnDrop.setOnClickListener  { onDrop(item.id) }
        }
    }
}

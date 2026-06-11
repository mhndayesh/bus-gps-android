package com.busgps.android.ui.admin

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemParentBinding
import com.busgps.android.model.Parent

class ParentListAdapter(private val parents: List<Parent>) :
    RecyclerView.Adapter<ParentListAdapter.VH>() {

    inner class VH(val binding: ItemParentBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemParentBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = parents.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val p = parents[position]
        holder.binding.apply {
            tvName.text = p.name
            tvId.text = p.id.take(8) + "…"
        }
    }
}

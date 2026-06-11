package com.busgps.android.ui.admin

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemDriverBinding
import com.busgps.android.model.Driver

class DriverListAdapter(private val drivers: List<Driver>) :
    RecyclerView.Adapter<DriverListAdapter.VH>() {

    inner class VH(val binding: ItemDriverBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemDriverBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = drivers.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val d = drivers[position]
        holder.binding.apply {
            tvName.text = d.name
            tvId.text = d.id.take(8) + "…"
        }
    }
}
